from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CalculationInput:
    concept_id: int
    fecha_multa: date
    fecha_liquidacion: date
    cantidad_unidades: Optional[float] = None
    valor_manual: Optional[float] = None
    tiene_programa_comunitario: bool = False


@dataclass
class CalculationResult:
    concept_name: str
    unidad_aplicada: str
    valor_unidad: float
    cantidad_unidades: float
    valor_base: float
    dias_transcurridos: int
    dias_mora: int
    aplica_descuento: bool
    porcentaje_descuento: float
    valor_descuento: float
    metodo_interes: str
    tasa_interes_anual: float
    valor_interes: float
    total_pagar: float
    regla_aplicada: str
