from __future__ import annotations

from typing import Optional

from .db import get_connection, hash_password

CATEGORY_ORDER = [
    'MULTAS_GENERALES',
    'MULTAS_ESPECIALES',
    'MULTAS_NO_TRIBUTARIAS',
    'OTRAS_MULTAS',
]


class UserRepository:
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute(
            'SELECT * FROM usuarios WHERE username = ? COLLATE NOCASE AND activo = 1',
            (username.strip(),),
        ).fetchone()
        conn.close()
        if not row:
            return None
        if row['password_hash'] != hash_password(password):
            return None
        return dict(row)

    @staticmethod
    def list_all() -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            'SELECT * FROM usuarios ORDER BY activo DESC, rol DESC, username COLLATE NOCASE'
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def create_user(username: str, password: str, rol: str, nombre: str = '', activo: bool = True, debe_cambiar_clave: bool = True) -> None:
        conn = get_connection()
        conn.execute(
            '''
            INSERT INTO usuarios (username, nombre, password_hash, rol, activo, debe_cambiar_clave)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                username.strip(),
                nombre.strip(),
                hash_password(password),
                rol,
                1 if activo else 0,
                1 if debe_cambiar_clave else 0,
            ),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def set_active(user_id: int, activo: bool) -> None:
        conn = get_connection()
        conn.execute('UPDATE usuarios SET activo = ? WHERE id = ?', (1 if activo else 0, user_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update_role(user_id: int, rol: str) -> None:
        conn = get_connection()
        conn.execute('UPDATE usuarios SET rol = ? WHERE id = ?', (rol, user_id))
        conn.commit()
        conn.close()

    @staticmethod
    def reset_password(user_id: int, provisional_password: str) -> None:
        conn = get_connection()
        conn.execute(
            'UPDATE usuarios SET password_hash = ?, debe_cambiar_clave = 1 WHERE id = ?',
            (hash_password(provisional_password), user_id),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        conn = get_connection()
        row = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
        if not row:
            conn.close()
            return False, 'Usuario no encontrado.'
        if row['password_hash'] != hash_password(old_password):
            conn.close()
            return False, 'La contraseña actual no es correcta.'
        conn.execute(
            'UPDATE usuarios SET password_hash = ?, debe_cambiar_clave = 0 WHERE id = ?',
            (hash_password(new_password), user_id),
        )
        conn.commit()
        conn.close()
        return True, 'Contraseña actualizada.'

    @staticmethod
    def must_change_password(user_id: int) -> bool:
        conn = get_connection()
        row = conn.execute('SELECT debe_cambiar_clave FROM usuarios WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return bool(row['debe_cambiar_clave']) if row else False

    @staticmethod
    def mark_login(user_id: int) -> None:
        conn = get_connection()
        conn.execute("UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def soft_delete(user_id: int) -> None:
        conn = get_connection()
        conn.execute('UPDATE usuarios SET activo = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def update_user(user_id: int, *, nombre: str = '', rol: str = 'liquidador', activo: bool = True) -> None:
        conn = get_connection()
        conn.execute(
            'UPDATE usuarios SET nombre = ?, rol = ?, activo = ? WHERE id = ?',
            (nombre.strip(), rol, 1 if activo else 0, user_id),
        )
        conn.commit()
        conn.close()


class ParameterRepository:
    @staticmethod
    def get_active() -> dict:
        conn = get_connection()
        row = conn.execute(
            'SELECT * FROM parametros_generales WHERE activo = 1 ORDER BY id DESC LIMIT 1'
        ).fetchone()
        conn.close()
        return dict(row)

    @staticmethod
    def update(
        dias_gracia: int,
        porcentaje_descuento: float,
        tasa_no_tributaria: float,
        permitir_editar_fecha_liquidacion: bool,
    ) -> None:
        conn = get_connection()
        conn.execute('UPDATE parametros_generales SET activo = 0 WHERE activo = 1')
        conn.execute(
            '''
            INSERT INTO parametros_generales (
                dias_gracia_descuento, porcentaje_descuento, tasa_no_tributaria,
                permitir_editar_fecha_liquidacion, activo
            ) VALUES (?, ?, ?, ?, 1)
            ''',
            (dias_gracia, porcentaje_descuento, tasa_no_tributaria, 1 if permitir_editar_fecha_liquidacion else 0),
        )
        conn.commit()
        conn.close()


class ConceptRepository:
    @staticmethod
    def list_active() -> list[dict]:
        conn = get_connection()
        rows = conn.execute('SELECT * FROM conceptos_multa WHERE activo = 1').fetchall()
        conn.close()
        items = [dict(r) for r in rows]
        order_map = {key: idx for idx, key in enumerate(CATEGORY_ORDER)}
        items.sort(key=lambda x: (order_map.get(x['categoria'], 99), x['nombre']))
        return items

    @staticmethod
    def get_by_id(concept_id: int) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute(
            'SELECT * FROM conceptos_multa WHERE id = ? AND activo = 1',
            (concept_id,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None


class UnitValueRepository:
    @staticmethod
    def get_value(anio: int, tipo_unidad: str) -> Optional[float]:
        conn = get_connection()
        row = conn.execute(
            'SELECT valor FROM valores_unidad WHERE anio = ? AND tipo_unidad = ? AND activo = 1',
            (anio, tipo_unidad),
        ).fetchone()
        conn.close()
        return float(row['valor']) if row else None

    @staticmethod
    def list_all() -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            'SELECT * FROM valores_unidad ORDER BY anio DESC, tipo_unidad'
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def upsert(anio: int, tipo_unidad: str, valor: float) -> None:
        conn = get_connection()
        conn.execute(
            '''
            INSERT INTO valores_unidad (anio, tipo_unidad, valor, activo)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(anio, tipo_unidad) DO UPDATE SET valor = excluded.valor, activo = 1
            ''',
            (anio, tipo_unidad, valor),
        )
        conn.commit()
        conn.close()


    @staticmethod
    def soft_delete(unit_id: int) -> None:
        conn = get_connection()
        conn.execute('UPDATE valores_unidad SET activo = 0 WHERE id = ?', (unit_id,))
        conn.commit()
        conn.close()


class InterestRateRepository:
    @staticmethod
    def get_rate(metodo_interes: str, anio: int, mes: int) -> Optional[float]:
        conn = get_connection()
        row = conn.execute(
            '''
            SELECT tasa_anual
            FROM tasas_interes
            WHERE metodo_interes = ? AND anio = ? AND mes = ? AND activo = 1
            ''',
            (metodo_interes, anio, mes),
        ).fetchone()
        conn.close()
        return float(row['tasa_anual']) if row else None

    @staticmethod
    def list_all() -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            'SELECT * FROM tasas_interes ORDER BY metodo_interes, anio DESC, mes DESC'
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def upsert(metodo_interes: str, anio: int, mes: int, tasa_anual: float) -> None:
        conn = get_connection()
        conn.execute(
            '''
            INSERT INTO tasas_interes (metodo_interes, anio, mes, tasa_anual, activo)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(metodo_interes, anio, mes) DO UPDATE SET tasa_anual = excluded.tasa_anual, activo = 1
            ''',
            (metodo_interes, anio, mes, tasa_anual),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def soft_delete(rate_id: int) -> None:
        conn = get_connection()
        conn.execute('UPDATE tasas_interes SET activo = 0 WHERE id = ?', (rate_id,))
        conn.commit()
        conn.close()
