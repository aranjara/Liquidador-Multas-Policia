from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
import sys

def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]

APP_DIR = get_app_dir()
DB_PATH = APP_DIR / "liquidador.db"

# Semillas tomadas del Excel compartido por el usuario.
SMLV_BY_YEAR = {
    2016: 689454.0,
    2017: 737717.0,
    2018: 781242.0,
    2019: 828116.0,
    2020: 877803.0,
    2021: 908526.0,
    2022: 1000000.0,
    2023: 1160000.0,
    2024: 1300000.0,
    2025: 1423500.0,
    2026: 1750905.0,
}

UVB_BY_YEAR = {
    2023: 10000.0,
    2024: 10951.0,
    2025: 11552.0,
    2026: 12110.0,
}

# Tasas anuales históricas (en porcentaje) para el cálculo de intereses.
INTEREST_RATES = [
    (2008, 1, 32.75), (2008, 2, 32.75), (2008, 3, 32.75), (2008, 4, 32.88), (2008, 5, 32.88), (2008, 6, 32.88),
    (2008, 7, 32.52), (2008, 8, 32.52), (2008, 9, 32.52), (2008, 10, 31.93), (2008, 11, 31.93), (2008, 12, 31.93),
    (2009, 1, 30.84), (2009, 2, 30.84), (2009, 3, 30.84), (2009, 4, 29.58), (2009, 5, 29.58), (2009, 6, 29.58),
    (2009, 7, 27.83), (2009, 8, 27.83), (2009, 9, 27.83), (2009, 10, 24.21), (2009, 11, 24.21), (2009, 12, 24.21),
    (2010, 1, 23.3), (2010, 2, 23.3), (2010, 3, 23.3), (2010, 4, 20.56), (2010, 5, 20.56), (2010, 6, 20.56),
    (2010, 7, 18.81), (2010, 8, 18.81), (2010, 9, 18.81), (2010, 10, 18.81), (2010, 11, 18.81), (2010, 12, 18.81),
    (2011, 1, 18.96), (2011, 2, 18.96), (2011, 3, 18.96), (2011, 4, 19.26), (2011, 5, 19.26), (2011, 6, 19.26),
    (2011, 7, 19.26), (2011, 8, 19.26), (2011, 9, 19.26), (2011, 10, 19.26), (2011, 11, 19.26), (2011, 12, 19.26),
    (2012, 1, 19.87), (2012, 2, 19.87), (2012, 3, 19.87), (2012, 4, 20.34), (2012, 5, 20.34), (2012, 6, 20.34),
    (2012, 7, 20.34), (2012, 8, 20.34), (2012, 9, 20.34), (2012, 10, 20.95), (2012, 11, 20.95), (2012, 12, 20.95),
    (2013, 1, 21.46), (2013, 2, 21.46), (2013, 3, 21.46), (2013, 4, 21.72), (2013, 5, 21.72), (2013, 6, 21.72),
    (2013, 7, 21.72), (2013, 8, 21.72), (2013, 9, 21.72), (2013, 10, 21.23), (2013, 11, 21.23), (2013, 12, 21.23),
    (2014, 1, 20.48), (2014, 2, 20.48), (2014, 3, 20.48), (2014, 4, 20.45), (2014, 5, 20.45), (2014, 6, 20.45),
    (2014, 7, 20.34), (2014, 8, 20.34), (2014, 9, 20.34), (2014, 10, 20.03), (2014, 11, 20.03), (2014, 12, 20.03),
    (2015, 1, 19.81), (2015, 2, 19.81), (2015, 3, 19.81), (2015, 4, 19.42), (2015, 5, 19.42), (2015, 6, 19.42),
    (2015, 7, 19.33), (2015, 8, 19.33), (2015, 9, 19.33), (2015, 10, 19.12), (2015, 11, 19.12), (2015, 12, 19.12),
    (2016, 1, 19.09), (2016, 2, 19.09), (2016, 3, 19.09), (2016, 4, 19.75), (2016, 5, 19.75), (2016, 6, 19.75),
    (2016, 7, 20.49), (2016, 8, 20.49), (2016, 9, 20.49), (2016, 10, 21.14), (2016, 11, 21.14), (2016, 12, 21.14),
    (2017, 1, 20.53), (2017, 2, 20.53), (2017, 3, 20.53), (2017, 4, 20.18), (2017, 5, 20.18), (2017, 6, 20.18),
    (2017, 7, 19.96), (2017, 8, 19.96), (2017, 9, 19.96), (2017, 10, 19.52), (2017, 11, 19.52), (2017, 12, 19.52),
    (2018, 1, 19.94), (2018, 2, 19.94), (2018, 3, 19.94), (2018, 4, 20.53), (2018, 5, 20.53), (2018, 6, 20.53),
    (2018, 7, 20.94), (2018, 8, 20.94), (2018, 9, 20.94), (2018, 10, 21.16), (2018, 11, 21.16), (2018, 12, 21.16),
    (2019, 1, 21.09), (2019, 2, 21.09), (2019, 3, 21.09), (2019, 4, 20.84), (2019, 5, 20.84), (2019, 6, 20.84),
    (2019, 7, 20.28), (2019, 8, 20.28), (2019, 9, 20.28), (2019, 10, 19.32), (2019, 11, 19.32), (2019, 12, 19.32),
    (2020, 1, 18.95), (2020, 2, 18.95), (2020, 3, 18.95), (2020, 4, 18.69), (2020, 5, 18.69), (2020, 6, 18.69),
    (2020, 7, 18.25), (2020, 8, 18.25), (2020, 9, 18.25), (2020, 10, 18.06), (2020, 11, 18.06), (2020, 12, 18.06),
    (2021, 1, 18.15), (2021, 2, 18.15), (2021, 3, 18.15), (2021, 4, 18.47), (2021, 5, 18.47), (2021, 6, 18.47),
    (2021, 7, 18.83), (2021, 8, 18.83), (2021, 9, 18.83), (2021, 10, 19.58), (2021, 11, 19.58), (2021, 12, 19.58),
    (2022, 1, 20.58), (2022, 2, 20.58), (2022, 3, 20.58), (2022, 4, 22.21), (2022, 5, 22.21), (2022, 6, 22.21),
    (2022, 7, 24.34), (2022, 8, 24.34), (2022, 9, 24.34), (2022, 10, 27.29), (2022, 11, 27.29), (2022, 12, 27.29),
    (2023, 1, 31.67), (2023, 2, 31.67), (2023, 3, 31.67), (2023, 4, 39.8), (2023, 5, 39.8), (2023, 6, 39.8),
    (2023, 7, 41.13), (2023, 8, 41.13), (2023, 9, 41.13), (2023, 10, 38.28), (2023, 11, 38.28), (2023, 12, 38.28),
    (2024, 1, 35.77), (2024, 2, 35.77), (2024, 3, 35.77), (2024, 4, 33.01), (2024, 5, 33.01), (2024, 6, 33.01),
    (2024, 7, 31.53), (2024, 8, 31.53), (2024, 9, 31.53), (2024, 10, 29.53), (2024, 11, 29.53), (2024, 12, 29.53),
    (2025, 1, 28.62), (2025, 2, 28.62), (2025, 3, 28.62), (2025, 4, 27.62), (2025, 5, 27.62), (2025, 6, 27.62),
    (2025, 7, 26.29), (2025, 8, 26.29), (2025, 9, 26.29), (2025, 10, 22.99), (2025, 11, 22.99), (2025, 12, 23.02),
    (2026, 1, 22.36), (2026, 2, 23.23), (2026, 3, 23.52),
]

GENERAL_FACTORS = {
    # tipo: (vigencia_desde, vigencia_hasta, unidad, factor)
    1: [(2016, 2021, 'SMDLV', 4.0), (2022, 2022, 'SMDLV', 2.0), (2023, 9999, 'UVB', 7.7)],
    2: [(2016, 2021, 'SMDLV', 8.0), (2022, 2022, 'SMDLV', 4.0), (2023, 9999, 'UVB', 15.5)],
    3: [(2016, 2021, 'SMDLV', 16.0), (2022, 2022, 'SMDLV', 8.0), (2023, 9999, 'UVB', 30.9)],
    4: [(2016, 2021, 'SMDLV', 32.0), (2022, 2022, 'SMDLV', 16.0), (2023, 9999, 'UVB', 61.9)],
}

SPECIAL_SANCTIONS = {
    'EVENTOS': 100.0,
    'URBANISMO': 30.0,
    'VISUAL': 10.0,
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row['name'] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()}
    if column not in existing:
        conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


def _seed_concepts(conn: sqlite3.Connection) -> None:
    rows = conn.execute('SELECT codigo, nombre, categoria FROM conceptos_multa WHERE activo = 1').fetchall()
    current = {(r['codigo'], r['nombre'], r['categoria']) for r in rows}
    expected = {
        ('MG-1', 'Tipo 1', 'MULTAS_GENERALES'),
        ('MG-2', 'Tipo 2', 'MULTAS_GENERALES'),
        ('MG-3', 'Tipo 3', 'MULTAS_GENERALES'),
        ('MG-4', 'Tipo 4', 'MULTAS_GENERALES'),
        ('ME-EVENTOS', 'Comportamientos de los organizadores de actividades que involucran aglomeraciones de público complejas', 'MULTAS_ESPECIALES'),
        ('ME-URBANISMO', 'Infracción urbanística', 'MULTAS_ESPECIALES'),
        ('ME-VISUAL', 'Contaminación visual', 'MULTAS_ESPECIALES'),
        ('OM-001', 'Otras Multas', 'OTRAS_MULTAS'),
        ('NT-001', 'Multas No Tributarias', 'MULTAS_NO_TRIBUTARIAS'),
    }
    if current == expected:
        return

    conn.execute('DELETE FROM conceptos_multa')
    concepts = [
        ('MG-1', 'Tipo 1', 'MULTAS_GENERALES', 'PESOS', None, None, 0, 1, 'TABLA_HISTORICA_GENERAL', 2016, None, 1),
        ('MG-2', 'Tipo 2', 'MULTAS_GENERALES', 'PESOS', None, None, 0, 1, 'TABLA_HISTORICA_GENERAL', 2016, None, 1),
        ('MG-3', 'Tipo 3', 'MULTAS_GENERALES', 'PESOS', None, None, 0, 1, 'TABLA_HISTORICA_GENERAL', 2016, None, 1),
        ('MG-4', 'Tipo 4', 'MULTAS_GENERALES', 'PESOS', None, None, 0, 1, 'TABLA_HISTORICA_GENERAL', 2016, None, 1),
        ('ME-EVENTOS', 'Comportamientos de los organizadores de actividades que involucran aglomeraciones de público complejas', 'MULTAS_ESPECIALES', 'PESOS', None, None, 0, 1, 'TABLA_HISTORICA_EVENTOS', 2016, None, 1),
        ('ME-URBANISMO', 'Infracción urbanística', 'MULTAS_ESPECIALES', 'PESOS', None, None, 0, 1, 'TABLA_HISTORICA_URBANISMO', 2016, None, 1),
        ('ME-VISUAL', 'Contaminación visual', 'MULTAS_ESPECIALES', 'PESOS', None, None, 0, 1, 'TABLA_HISTORICA_VISUAL', 2016, None, 1),
        ('OM-001', 'Otras Multas', 'OTRAS_MULTAS', 'PESOS', None, None, 1, 1, 'TABLA_HISTORICA_OTRAS', 2016, None, 1),
        ('NT-001', 'Multas No Tributarias', 'MULTAS_NO_TRIBUTARIAS', 'PESOS', None, None, 1, 1, 'NO_TRIBUTARIA_FIJA', 2016, None, 1),
    ]
    conn.executemany(
        '''
        INSERT INTO conceptos_multa (
            codigo, nombre, categoria, unidad_calculo, cantidad_unidades, valor_fijo,
            usa_valor_fijo, usa_descuento, metodo_interes, vigencia_desde, vigencia_hasta, activo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        concepts,
    )



def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nombre TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('admin', 'liquidador')),
            activo INTEGER NOT NULL DEFAULT 1,
            debe_cambiar_clave INTEGER NOT NULL DEFAULT 0,
            ultimo_acceso TEXT
        );

        CREATE TABLE IF NOT EXISTS parametros_generales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dias_gracia_descuento INTEGER NOT NULL,
            porcentaje_descuento REAL NOT NULL,
            tasa_no_tributaria REAL NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS valores_unidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anio INTEGER NOT NULL,
            tipo_unidad TEXT NOT NULL CHECK (tipo_unidad IN ('PESOS', 'SMMLV', 'SMDLV', 'UVB')),
            valor REAL NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            UNIQUE(anio, tipo_unidad)
        );

        CREATE TABLE IF NOT EXISTS conceptos_multa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad_calculo TEXT NOT NULL CHECK (unidad_calculo IN ('PESOS', 'SMMLV', 'SMDLV', 'UVB')),
            cantidad_unidades REAL,
            valor_fijo REAL,
            usa_valor_fijo INTEGER NOT NULL DEFAULT 0,
            usa_descuento INTEGER NOT NULL DEFAULT 1,
            metodo_interes TEXT NOT NULL,
            vigencia_desde INTEGER NOT NULL,
            vigencia_hasta INTEGER,
            activo INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS tasas_interes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metodo_interes TEXT NOT NULL,
            anio INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            tasa_anual REAL NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            UNIQUE(metodo_interes, anio, mes)
        );
        """
    )

    _ensure_column(conn, 'parametros_generales', 'permitir_editar_fecha_liquidacion', 'INTEGER NOT NULL DEFAULT 0')
    _ensure_column(conn, 'usuarios', 'nombre', "TEXT DEFAULT ''")
    _ensure_column(conn, 'usuarios', 'debe_cambiar_clave', 'INTEGER NOT NULL DEFAULT 0')
    _ensure_column(conn, 'usuarios', 'ultimo_acceso', 'TEXT')

    cur.execute('SELECT COUNT(*) AS total FROM usuarios')
    if cur.fetchone()['total'] == 0:
        cur.execute(
            'INSERT INTO usuarios (username, nombre, password_hash, rol, activo, debe_cambiar_clave) VALUES (?, ?, ?, ?, 1, 0)',
            ('admin', 'Administrador', hash_password('admin123'), 'admin'),
        )
        cur.execute(
            'INSERT INTO usuarios (username, nombre, password_hash, rol, activo, debe_cambiar_clave) VALUES (?, ?, ?, ?, 1, 0)',
            ('liquidador', 'Liquidador', hash_password('123456'), 'liquidador'),
        )

    cur.execute('SELECT COUNT(*) AS total FROM parametros_generales')
    if cur.fetchone()['total'] == 0:
        cur.execute(
            'INSERT INTO parametros_generales (dias_gracia_descuento, porcentaje_descuento, tasa_no_tributaria, permitir_editar_fecha_liquidacion, activo) VALUES (?,?,?,?,1)',
            (8, 50.0, 12.0, 0),
        )

    cur.execute('SELECT COUNT(*) AS total FROM valores_unidad')
    if cur.fetchone()['total'] == 0:
        for anio, smlv in SMLV_BY_YEAR.items():
            cur.execute(
                'INSERT INTO valores_unidad (anio, tipo_unidad, valor, activo) VALUES (?, ?, ?, 1)',
                (anio, 'SMMLV', smlv),
            )
            cur.execute(
                'INSERT INTO valores_unidad (anio, tipo_unidad, valor, activo) VALUES (?, ?, ?, 1)',
                (anio, 'SMDLV', round(smlv / 30.0, 2)),
            )
        for anio, uvb in UVB_BY_YEAR.items():
            cur.execute(
                'INSERT INTO valores_unidad (anio, tipo_unidad, valor, activo) VALUES (?, ?, ?, 1)',
                (anio, 'UVB', uvb),
            )

    _seed_concepts(conn)

    cur.execute('SELECT COUNT(*) AS total FROM tasas_interes')
    total_rates = cur.fetchone()['total']
    if total_rates < 200:
        cur.execute('DELETE FROM tasas_interes')
        methods = [
            'TABLA_HISTORICA_GENERAL',
            'TABLA_HISTORICA_EVENTOS',
            'TABLA_HISTORICA_VISUAL',
            'TABLA_HISTORICA_URBANISMO',
            'TABLA_HISTORICA_OTRAS',
        ]
        rows = []
        for metodo in methods:
            rows.extend((metodo, anio, mes, tasa, 1) for anio, mes, tasa in INTEREST_RATES)
        cur.executemany(
            'INSERT INTO tasas_interes (metodo_interes, anio, mes, tasa_anual, activo) VALUES (?, ?, ?, ?, ?)',
            rows,
        )

    conn.commit()
    conn.close()
