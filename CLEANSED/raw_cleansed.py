import os
import sys
from conexiones import get_snowflake_connection
from reglas_calidad import REGLAS_CALIDAD
sys.dont_write_bytecode = True # Evita la creación de archivos .pyc para mantener el proyecto limpio

_DIR = os.path.dirname(os.path.abspath(__file__))


def _cargar_sql(nombre, seccion=None, **kw):
    with open(os.path.join(_DIR, nombre), encoding='utf-8') as f:
        sql = f.read()
    if seccion:
        tag = f'-- [{seccion}]'
        inicio = sql.index(tag) + len(tag)
        siguiente = sql.find('-- [', inicio)
        sql = sql[inicio : siguiente if siguiente != -1 else None].strip()
    return sql.format(**kw) if kw else sql


def construir_condicion_calidad(reglas, alias=None):
    condiciones = []
    for regla in reglas:
        col = f"{alias}.{regla['columna']}" if alias else regla['columna']

        if regla["regla"] == "not_null":
            condiciones.append(f"{col} IS NOT NULL")
        elif regla["regla"] == "positive":
            condiciones.append(f"{col} > 0")
        elif regla["regla"] == "non_negative":
            condiciones.append(f"{col} >= 0")
        elif regla["regla"] == "allowed_values":
            valores = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in regla["valores"]])
            condiciones.append(f"{col} IN ({valores})")
        elif regla["regla"] == "regex":
            condiciones.append(f"REGEXP_LIKE({col}, '{regla['patron']}')")
        elif regla["regla"] == "range":
            condiciones.append(f"{col} >= {regla['min']} AND {col} <= {regla['max']}")

    return " AND ".join(condiciones) if condiciones else "1=1"


def desplegar_capa_cleansed_automatica():
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(_cargar_sql("selects.sql", "DETECTIVE"))
        tablas = cursor.fetchall()

        for esquema_raw, nombre_tabla, clave_primaria in tablas:
            esquema_cleansed   = esquema_raw.replace("RAW_", "CLEANSED_")
            nombre_proyecto    = esquema_raw.replace("RAW_", "")
            nombre_tabla_lower = nombre_tabla.lower()

            print(f"[CONFIG] Configurando: {nombre_tabla} | PK: {clave_primaria}")

            cursor.execute(_cargar_sql("selects.sql", "COLUMNAS", esquema=esquema_raw, nombre_tabla=nombre_tabla))
            columnas       = [row[0] for row in cursor.fetchall()]
            columnas_upper = [c.upper() for c in columnas]

            if "FECHA_MODIFICACION" in columnas_upper:
                orden_cdc = "FECHA_MODIFICACION DESC"
            elif "FECHA_REGISTRO" in columnas_upper:
                orden_cdc = "FECHA_REGISTRO DESC"
            else:
                orden_cdc = "_DLT_LOAD_ID DESC"

            update_set  = ", ".join([f"{col} = source.{col}" for col in columnas])
            insert_cols = ", ".join(columnas)
            insert_vals = ", ".join([f"source.{col}" for col in columnas])

            reglas = REGLAS_CALIDAD.get(nombre_tabla_lower, [])

            if reglas:
                cond_valida = construir_condicion_calidad(reglas)
                condicion_valida_inicial   = cond_valida
                # CASE WHEN maneja NULLs: fila invalida si cualquier condicion no se cumple
                condicion_invalida_inicial = f"CASE WHEN {cond_valida} THEN TRUE ELSE FALSE END = FALSE"
                condicion_valida_merge     = cond_valida
                condicion_invalida_merge   = f"CASE WHEN {cond_valida} THEN TRUE ELSE FALSE END = FALSE"
                print(f"    {len(reglas)} reglas detectadas.")
            else:
                condicion_valida_inicial   = "1=1"
                condicion_invalida_inicial = "1=0"
                condicion_valida_merge     = "1=1"
                condicion_invalida_merge   = "1=0"
                print(f"   Sin reglas definidas. Todo pasa a CLEANSED.")

            nombre_stream = f"STREAMS.STREAM_CLEANSED_{nombre_proyecto}_{nombre_tabla}"
            nombre_task   = f"TASKS.TASK_CLEANSED_{nombre_proyecto}_{nombre_tabla}"

            conn.execute_string(_cargar_sql(
                "streams_tasks.sql", "SETUP",
                esquema_cleansed=esquema_cleansed,
                esquema_raw=esquema_raw,
                nombre_tabla=nombre_tabla,
                nombre_stream=nombre_stream,
                condicion_valida_inicial=condicion_valida_inicial,
                condicion_invalida_inicial=condicion_invalida_inicial,
            ))

            cursor.execute(_cargar_sql(
                "streams_tasks.sql", "TASK",
                nombre_task=nombre_task,
                nombre_stream=nombre_stream,
                esquema_cleansed=esquema_cleansed,
                nombre_tabla=nombre_tabla,
                clave_primaria=clave_primaria,
                orden_cdc=orden_cdc,
                condicion_valida_merge=condicion_valida_merge,
                condicion_invalida_merge=condicion_invalida_merge,
                update_set=update_set,
                insert_cols=insert_cols,
                insert_vals=insert_vals,
            ))
            cursor.execute(f"ALTER TASK {nombre_task} RESUME")

            print(f"    {nombre_tabla} desplegada correctamente.")

        print("\n Capa CLEANSED desplegada correctamente")

    except Exception as e:
        print(f" Error en el despliegue CLEANSED: {e}")
        raise

    finally:
        conn.close()
        print(" Conexion cerrada de forma segura.")
