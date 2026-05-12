import sys
sys.dont_write_bytecode = True
import re
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy import types as sa_types

#NORMALIZACION INTERNA DE DLT 
#para que no haya problemas con mayusculas,guiones y espacios
def _to_snake_case(name: str) -> str:
    """Convierte CamelCase a snake_case para que coincida con la normalización interna de dlt."""
    name = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name)
    return name.lower()

#PARA LA CARGA INCREMENTAL: WATERMARK Y FILTRADO EN ORIGEN
#funcionamieno: get_watermark obtiene el maximo valor del campo de fecha en la tabla destino (Snowflake) 
# para saber hasta donde se ha cargado. Si no hay datos, devuelve None.
def get_watermark(sf_conn, schema, tabla, campo_cursor):
    """Devuelve el MAX de la columna de fecha ya cargada en Snowflake para esa tabla.
    Devuelve None si la tabla no existe o está vacía (primera carga: SELECT * sin filtro)."""
    col_name = _to_snake_case(campo_cursor)
    cursor = sf_conn.cursor()
    try:
        cursor.execute(f"SELECT MAX({col_name}) FROM {schema}.{tabla}")
        return cursor.fetchone()[0]
    except Exception as e:
        if "42S02" not in str(e) and "does not exist" not in str(e).lower():
            print(f"     [!] get_watermark({schema}.{tabla}): {e}")
        return None
    finally:
        cursor.close()

#PARA LA CARGA INCREMENTAL: EJECUTAR SELECT CON FILTRO DE WATERMARK
def fetch_filas_incremental(conn, tabla_origen, campo_cursor, watermark, ingestion_time):
    """Ejecuta SELECT sobre la tabla origen con filtro incremental si hay watermark.
    Devuelve lista de dicts con fecha_ingestion añadida."""
    if watermark is None:
        result = conn.execute(sa.text(f"SELECT * FROM {tabla_origen}"))
    else:
        # Snowflake almacena timestamps con precision de ms (3 decimales). SQL Server datetime
        # usa ticks de 1/300s (3.333ms). El watermark de Snowflake pierde la fraccion de tick
        # (ej: SQL Server 943.333ms -> Snowflake 943ms). Con +1ms el umbral queda en 944ms,
        # que excluye el tick actual (943.333ms) pero incluye el siguiente (946.666ms).
        # Es seguro porque entre ticks consecutivos de SQL Server hay minimo 3.333ms.
        wm = watermark.replace(tzinfo=None) if getattr(watermark, 'tzinfo', None) else watermark
        wm = wm + timedelta(milliseconds=1)
        result = conn.execute(
            sa.text(f"SELECT * FROM {tabla_origen} WHERE {campo_cursor} > :wm"),
            {"wm": wm}
        )
    return [{**dict(row._mapping), "fecha_ingestion": ingestion_time} for row in result]

#ESTO ES PARA LOS TIPOS DE COLUMNAS EN DLT SEAN LOS CORRECTOS Y NO TODOS TEXT
def _sa_type_to_dlt(sa_type):
    """Mapea un tipo SQLAlchemy al tipo dlt equivalente."""
    if isinstance(sa_type, (sa_types.Integer, sa_types.SmallInteger, sa_types.BigInteger)):
        return "bigint"
    if isinstance(sa_type, (sa_types.String, sa_types.Text, sa_types.Unicode, sa_types.UnicodeText)):
        return "text"
    if isinstance(sa_type, sa_types.Float):
        return "double"
    if isinstance(sa_type, (sa_types.Numeric,)):
        return "decimal"
    if isinstance(sa_type, (sa_types.DateTime, sa_types.TIMESTAMP)):
        return "timestamp"
    if isinstance(sa_type, sa_types.Date):
        return "date"
    if isinstance(sa_type, sa_types.Time):
        return "time"
    if isinstance(sa_type, sa_types.Boolean):
        return "bool"
    return "text"

#ESTO ES PARA LEER EL SCHEMA DE LA TABLA EN EL ORIGEN Y DEVOLVER LOS TYPE HINTS PARA DLT
def get_column_hints(engine, tabla_origen):
    """Lee el schema de la tabla en el origen y devuelve los type hints para dlt.
    Las claves se normalizan a snake_case para que coincidan con la normalización de dlt.
    Incluye siempre fecha_ingestion como timestamp."""
    inspector = sa.inspect(engine)
    columnas = inspector.get_columns(tabla_origen)
    hints = {
        _to_snake_case(col["name"]): {"data_type": _sa_type_to_dlt(col["type"]), "nullable": True}
        for col in columnas
    }
    hints["fecha_ingestion"] = {"data_type": "timestamp", "nullable": False}
    return hints
