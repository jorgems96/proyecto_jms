import os
import sys
from conexiones import get_snowflake_connection
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


def desplegar_capa_raw_automatica():
    print("Iniciando escaneo de LANDING y detectando Claves Primarias...")

    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(_cargar_sql("selects.sql", "DETECTIVE"))
        tablas_con_pk = cursor.fetchall()

        for esquema_landing, nombre_tabla, clave_primaria in tablas_con_pk:
            esquema_raw     = esquema_landing.replace('LANDING_', 'RAW_')
            nombre_proyecto = esquema_landing.replace('LANDING_', '')

            print(f"[CONFIG] Configurando: {nombre_tabla} | PK Detectada: {clave_primaria}")

            cursor.execute(_cargar_sql("selects.sql", "COLUMNAS", esquema=esquema_landing, nombre_tabla=nombre_tabla))
            columnas       = [row[0] for row in cursor.fetchall()]
            columnas_upper = [c.upper() for c in columnas]

            if "FECHA_MODIFICACION" in columnas_upper:
                orden_cdc = "FECHA_MODIFICACION DESC"
            elif "FECHA_REGISTRO" in columnas_upper:
                orden_cdc = "FECHA_REGISTRO DESC"
            else:
                orden_cdc = "_dlt_load_id DESC"

            update_set  = ", ".join([f"{col} = source.{col}" for col in columnas])
            insert_cols = ", ".join(columnas)
            insert_vals = ", ".join([f"source.{col}" for col in columnas])

            posibles_nombres_borrado = ["_IS_DELETED", "_DLT_DELETED", "IS_DELETED", "BORRADO"]
            col_borrado = next((c for c in columnas_upper if c in posibles_nombres_borrado), None)

            if col_borrado:
                clausula_borrado_logico = f"WHEN MATCHED AND source.{col_borrado} = TRUE THEN DELETE"
                print(f"   [BORRADO LOGICO] Columna detectada: {col_borrado}")
            else:
                clausula_borrado_logico = "-- No aplica borrado logico: No se detecto columna indicadora."

            conn.execute_string(_cargar_sql(
                "streams_tasks.sql",
                esquema_raw=esquema_raw,
                esquema_landing=esquema_landing,
                nombre_tabla=nombre_tabla,
                nombre_proyecto=nombre_proyecto,
                clave_primaria=clave_primaria,
                orden_cdc=orden_cdc,
                clausula_borrado_logico=clausula_borrado_logico,
                update_set=update_set,
                insert_cols=insert_cols,
                insert_vals=insert_vals,
            ))

        print(" Capa RAW automatizada al 100%. Mantenimiento cero conseguido.")

    except Exception as e:
        print(f" Error en el despliegue RAW: {e}")
        raise

    finally:
        conn.close()
        print(" Conexion a Snowflake cerrada de forma segura.")
