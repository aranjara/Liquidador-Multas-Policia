from __future__ import annotations

from datetime import date, timedelta

from .db import GENERAL_FACTORS
from .models import CalculationInput, CalculationResult
from .repositories import ConceptRepository, InterestRateRepository, ParameterRepository, UnitValueRepository


class LiquidationError(Exception):
    pass


class LiquidationService:
    @staticmethod
    def calcular(data: CalculationInput) -> CalculationResult:
        concept = ConceptRepository.get_by_id(data.concept_id)
        if not concept:
            raise LiquidationError('No se encontró el concepto de multa seleccionado.')

        if data.fecha_liquidacion < data.fecha_multa:
            raise LiquidationError('La fecha de liquidación no puede ser menor a la fecha de la multa.')

        anio_multa = data.fecha_multa.year
        if anio_multa < concept['vigencia_desde']:
            raise LiquidationError('La fecha de multa es anterior a la vigencia del concepto.')
        if concept['vigencia_hasta'] and anio_multa > concept['vigencia_hasta']:
            raise LiquidationError('La fecha de multa está por fuera de la vigencia del concepto.')

        params = ParameterRepository.get_active()
        valor_base, unidad_aplicada, valor_unidad, cantidad_unidades = LiquidationService._resolver_base(concept, data)

        dias_transcurridos = (data.fecha_liquidacion - data.fecha_multa).days
        aplica_descuento = bool(concept['usa_descuento']) and dias_transcurridos <= int(params['dias_gracia_descuento'])
        porcentaje_descuento = LiquidationService._resolver_descuento(concept, data, aplica_descuento, float(params['porcentaje_descuento']))
        valor_descuento = round(valor_base * (porcentaje_descuento / 100.0), 2)

        valor_interes, tasa_interes_anual, dias_mora = LiquidationService._calcular_interes(
            valor_base=valor_base,
            fecha_multa=data.fecha_multa,
            fecha_liquidacion=data.fecha_liquidacion,
            metodo_interes=concept['metodo_interes'],
            tasa_no_tributaria=float(params['tasa_no_tributaria']),
            dias_gracia_descuento=int(params['dias_gracia_descuento']),
        )

        total = round(valor_base - valor_descuento + valor_interes, 2)
        regla = (
            f'Base en {unidad_aplicada}; descuento {porcentaje_descuento:.2f}%; '
            f'interés por {concept["metodo_interes"]}; mora {dias_mora} día(s)'
        )

        return CalculationResult(
            concept_name=concept['nombre'],
            unidad_aplicada=unidad_aplicada,
            valor_unidad=valor_unidad,
            cantidad_unidades=cantidad_unidades,
            valor_base=round(valor_base, 2),
            dias_transcurridos=dias_transcurridos,
            dias_mora=dias_mora,
            aplica_descuento=aplica_descuento,
            porcentaje_descuento=porcentaje_descuento,
            valor_descuento=round(valor_descuento, 2),
            metodo_interes=concept['metodo_interes'],
            tasa_interes_anual=round(tasa_interes_anual, 4),
            valor_interes=round(valor_interes, 2),
            total_pagar=total,
            regla_aplicada=regla,
        )

    @staticmethod
    def _resolver_descuento(concept: dict, data: CalculationInput, aplica_descuento: bool, porcentaje_general: float) -> float:
        if not aplica_descuento:
            return 0.0
        if concept['codigo'] in ('MG-3', 'MG-4'):
            return 75.0 if data.tiene_programa_comunitario else 50.0
        return porcentaje_general

    @staticmethod
    def _resolver_base(concept: dict, data: CalculationInput) -> tuple[float, str, float, float]:
        codigo = concept['codigo']
        year = data.fecha_multa.year

        if codigo.startswith('MG-'):
            tipo = int(codigo.split('-')[1])
            for start, end, unidad, factor in GENERAL_FACTORS[tipo]:
                if start <= year <= end:
                    valor_unidad = UnitValueRepository.get_value(year, unidad)
                    if valor_unidad is None:
                        raise LiquidationError(f'No existe valor configurado para {unidad} en el año {year}.')
                    valor_base = LiquidationService._round_excel((valor_unidad * factor))
                    return valor_base, unidad, float(valor_unidad), factor
            raise LiquidationError(f'No hay regla de multa general configurada para el año {year}.')

        if codigo in ('ME-EVENTOS', 'ME-URBANISMO', 'ME-VISUAL'):
            if data.cantidad_unidades in (None, ''):
                raise LiquidationError('Debes seleccionar la Cantidad SMMLV o UVB según corresponda.')
            cantidad = float(data.cantidad_unidades)
            unidad = 'SMMLV' if year <= 2022 else 'UVB'
            valor_unidad = UnitValueRepository.get_value(year, unidad)
            if valor_unidad is None:
                raise LiquidationError(f'No existe valor configurado para {unidad} en el año {year}.')
            return LiquidationService._round_excel(cantidad * valor_unidad), unidad, float(valor_unidad), cantidad

        if codigo in ('OM-001', 'NT-001'):
            if data.valor_manual is None:
                raise LiquidationError('Debes ingresar el Valor Sanción para este concepto.')
            return float(data.valor_manual), 'PESOS', 1.0, 1.0

        if concept['usa_valor_fijo']:
            valor = float(data.valor_manual) if data.valor_manual is not None else float(concept['valor_fijo'] or 0)
            return valor, 'PESOS', 1.0, 1.0

        unidad = concept['unidad_calculo']
        cantidad = float(data.cantidad_unidades if data.cantidad_unidades not in (None, '') else concept['cantidad_unidades'] or 0)
        valor_unidad = UnitValueRepository.get_value(year, unidad)
        if valor_unidad is None:
            raise LiquidationError(f'No existe valor configurado para {unidad} en el año {year}.')
        return cantidad * valor_unidad, unidad, float(valor_unidad), cantidad

    @staticmethod
    def _calcular_interes(
        valor_base: float,
        fecha_multa: date,
        fecha_liquidacion: date,
        metodo_interes: str,
        tasa_no_tributaria: float,
        dias_gracia_descuento: int,
    ) -> tuple[float, float, int]:
        if fecha_liquidacion <= fecha_multa:
            return 0.0, 0.0, 0

        if metodo_interes == 'NO_TRIBUTARIA_FIJA':
            dias = max((fecha_liquidacion - fecha_multa).days, 0)
            if dias <= 0:
                return 0.0, 0.0, 0
            interes = LiquidationService._round_excel(valor_base * (tasa_no_tributaria / 100.0) * (dias / 365.0))
            return interes, tasa_no_tributaria, dias

        fecha_vencimiento = fecha_multa + timedelta(days=dias_gracia_descuento)
        if fecha_liquidacion <= fecha_vencimiento:
            return 0.0, 0.0, 0

        dias_mora = (fecha_liquidacion - fecha_vencimiento).days

        # El Excel histórico de intereses DIAN no liquida mes a mes de forma plana:
        # acumula los días por trimestre y aplica la tasa del último mes del tramo
        # (o del mes de pago si el trimestre queda incompleto).
        inicio_mora = fecha_vencimiento + timedelta(days=1)
        cursor = date(inicio_mora.year, inicio_mora.month, 1)
        fin = date(fecha_liquidacion.year, fecha_liquidacion.month, 1)

        dias_tramo = 0
        total_interes = 0.0
        last_rate = 0.0

        while cursor <= fin:
            month_start = date(cursor.year, cursor.month, 1)
            next_month = date(cursor.year + (1 if cursor.month == 12 else 0), 1 if cursor.month == 12 else cursor.month + 1, 1)
            month_end = next_month - timedelta(days=1)

            segment_start = max(inicio_mora, month_start)
            segment_end = min(fecha_liquidacion, month_end)
            dias_mes = 0
            if segment_end >= segment_start:
                dias_mes = (segment_end - segment_start).days + 1

            dias_tramo += dias_mes
            tasa = InterestRateRepository.get_rate(metodo_interes, cursor.year, cursor.month) or 0.0
            last_rate = tasa

            es_fin_trimestre = cursor.month in (3, 6, 9, 12)
            es_mes_pago = cursor.year == fecha_liquidacion.year and cursor.month == fecha_liquidacion.month

            if dias_tramo > 0 and (es_fin_trimestre or es_mes_pago):
                interes_tramo = valor_base * (tasa / 100.0) * (dias_tramo / 365.0)
                total_interes += LiquidationService._round_excel(interes_tramo)
                dias_tramo = 0

            cursor = next_month

        return LiquidationService._round_excel(total_interes), last_rate, dias_mora

    @staticmethod
    def _round_excel(value: float) -> float:
        # Emula ROUND(x, -3) usado en el Excel.
        return round(value / 1000.0) * 1000.0
