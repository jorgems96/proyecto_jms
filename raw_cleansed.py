# raw_cleansed.py
from conexiones import get_snowflake_connection
from reglas_calidad import REGLAS_CALIDAD

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
        query_detective = """
            SELECT
                t.TABLE_SCHEMA,
                t.TABLE_NAME,
                c.COLUMN_NAME AS CLAVE_PRIMARIA
            FROM INFORMATION_SCHEMA.TABLES t
            JOIN INFORMATION_SCHEMA.COLUMNS c
              ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
             AND t.TABLE_NAME = c.TABLE_NAME
            WHERE t.TABLE_SCHEMA LIKE 'RAW_%'
              AND t.TABLE_TYPE = 'BASE TABLE'
              AND NOT STARTSWITH(t.TABLE_NAME, '_DLT')
              AND STARTSWITH(c.COLUMN_NAME, 'ID_')
            QUALIFY ROW_NUMBER() OVER (PARTITION BY t.TABLE_NAME ORDER BY c.ORDINAL_POSITION) = 1;
        """

        cursor = conn.cursor()
        cursor.execute(query_detective)
        tablas = cursor.fetchall()

        for esquema_raw, nombre_tabla, clave_primaria in tablas:
            esquema_cleansed   = esquema_raw.replace("RAW_", "CLEANSED_")
            nombre_proyecto    = esquema_raw.replace("RAW_", "")
            nombre_tabla_lower = nombre_tabla.lower()

            print(f"[CONFIG] Configurando: {nombre_tabla} | PK: {clave_primaria}")

            cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{esquema_raw}'
                  AND TABLE_NAME   = '{nombre_tabla}'
                ORDER BY ORDINAL_POSITION
            """)
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
                # CASE WHEN para manejar NULLs correctamente: cualquier fila que no satisfaga
                # todas las condiciones (incluyendo UNKNOWN por NULLs) va a ERRORS
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

            # Esquemas, tablas iniciales y stream: sentencias simples, seguras para execute_string
            script_setup = f"""
            CREATE SCHEMA IF NOT EXISTS {esquema_cleansed};
            CREATE SCHEMA IF NOT EXISTS STREAMS;
            CREATE SCHEMA IF NOT EXISTS TASKS;

            CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}
            AS SELECT * FROM {esquema_raw}.{nombre_tabla}
            WHERE {condicion_valida_inicial};

            CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}_ERRORS
            AS SELECT * FROM {esquema_raw}.{nombre_tabla}
            WHERE {condicion_invalida_inicial};

            CREATE OR REPLACE STREAM {nombre_stream} ON TABLE {esquema_raw}.{nombre_tabla};
            """
            conn.execute_string(script_setup)

            # Task con bloque BEGIN...END: un único Stream, dos MERGEs en la misma transacción.
            # Snowflake lee el Stream una sola vez y reparte las filas entre CLEANSED y CLEANSED_ERRORS
            # antes de avanzar el offset del Stream al hacer commit.
            # Se ejecuta con cursor.execute() para enviar el bloque completo como un único comando
            # y evitar que execute_string lo parta por los ';' internos del BEGIN...END.
            sql_task = f"""
            CREATE OR REPLACE TASK {nombre_task}
            WAREHOUSE = COMPUTE_WH
            SCHEDULE = '5 MINUTE'
            WHEN SYSTEM$STREAM_HAS_DATA('{nombre_stream}')
            AS
            BEGIN
              MERGE INTO {esquema_cleansed}.{nombre_tabla} AS target
              USING (
                  SELECT *, METADATA$ACTION AS ACCION_CDC
                  FROM {nombre_stream}
                  WHERE {condicion_valida_merge}
                  QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
              ) AS source
              ON target.{clave_primaria} = source.{clave_primaria}
              WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
              WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
              WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

              MERGE INTO {esquema_cleansed}.{nombre_tabla}_ERRORS AS target
              USING (
                  SELECT *, METADATA$ACTION AS ACCION_CDC
                  FROM {nombre_stream}
                  WHERE {condicion_invalida_merge}
                  QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
              ) AS source
              ON target.{clave_primaria} = source.{clave_primaria}
              WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
              WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
              WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});
            END
            """
            cursor.execute(sql_task)
            cursor.execute(f"ALTER TASK {nombre_task} RESUME")

            print(f"    {nombre_tabla} desplegada correctamente.")

        print("\n Capa CLEANSED desplegada correctamente")

    except Exception as e:
        print(f" Error en el despliegue CLEANSED: {e}")
        raise

    finally:
        conn.close()
        print(" Conexion cerrada de forma segura.")
