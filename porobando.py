# raw_cleansed.py
from conexiones import get_snowflake_connection
from reglas_calidad import REGLAS_CALIDAD

def construir_condicion_calidad(reglas, alias="source"):
    """
    Traduce el diccionario de reglas de calidad a una condicion SQL WHERE.
    Devuelve la condicion que deben cumplir las filas VALIDAS.
    """
    condiciones = []

    for regla in reglas:
        col = f"{alias}.{regla['columna']}"

        if regla["regla"] == "not_null":
            condiciones.append(f"{col} IS NOT NULL")

        elif regla["regla"] == "positive":
            condiciones.append(f"{col} > 0")

        elif regla["regla"] == "allowed_values":
            valores = ", ".join([f"'{v}'" for v in regla["valores"]])
            condiciones.append(f"{col} IN ({valores})")

        elif regla["regla"] == "regex":
            condiciones.append(f"REGEXP_LIKE({col}, '{regla['patron']}')")

        elif regla["regla"] == "range":
            condiciones.append(f"{col} >= {regla['min']} AND {col} <= {regla['max']}")

    return " AND ".join(condiciones) if condiciones else "1=1"


def desplegar_capa_cleansed_automatica():
    print("Iniciando despliegue de capa CLEANSED con reglas de calidad...")

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

            print(f"Configurando: {nombre_tabla} | PK: {clave_primaria}")

            # Obtenemos columnas de la tabla RAW
            cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{esquema_raw}'
                  AND TABLE_NAME   = '{nombre_tabla}'
                ORDER BY ORDINAL_POSITION
            """)
            columnas       = [row[0] for row in cursor.fetchall()]
            columnas_upper = [c.upper() for c in columnas]

            # Orden CDC
            if "FECHA_MODIFICACION" in columnas_upper:
                orden_cdc = "FECHA_MODIFICACION DESC"
            elif "FECHA_REGISTRO" in columnas_upper:
                orden_cdc = "FECHA_REGISTRO DESC"
            else:
                orden_cdc = "_dlt_load_id DESC"

            # Construccion dinamica de columnas para MERGE
            update_set  = ", ".join([f"{col} = source.{col}" for col in columnas])
            insert_cols = ", ".join(columnas)
            insert_vals = ", ".join([f"source.{col}" for col in columnas])

            # Reglas de calidad para esta tabla
            reglas = REGLAS_CALIDAD.get(nombre_tabla_lower, [])

            if reglas:
                condicion_valida   = construir_condicion_calidad(reglas, alias="source")
                condicion_invalida = f"NOT ({condicion_valida})"
                # Para la carga inicial usamos sin alias
                condicion_valida_inicial   = construir_condicion_calidad(reglas, alias="")
                condicion_invalida_inicial = f"NOT ({condicion_valida_inicial})"
                print(f"   {len(reglas)} reglas de calidad aplicadas.")
            else:
                condicion_valida           = "1=1"
                condicion_invalida         = "1=0"
                condicion_valida_inicial   = "1=1"
                condicion_invalida_inicial = "1=0"
                print(f"   Sin reglas de calidad definidas. Todos los datos pasan a CLEANSED.")

            script_sql = f"""
            -- 0. Creamos los esquemas si no existen
            CREATE SCHEMA IF NOT EXISTS {esquema_cleansed};
            CREATE SCHEMA IF NOT EXISTS STREAMS;
            CREATE SCHEMA IF NOT EXISTS TASKS;

            -- 1. Carga inicial: filas VALIDAS -> CLEANSED.NombreTabla
            CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}
            AS SELECT * FROM {esquema_raw}.{nombre_tabla}
            WHERE {condicion_valida_inicial};

            -- 2. Carga inicial: filas INVALIDAS -> CLEANSED.NombreTabla_ERRORS
            CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}_ERRORS
            AS SELECT * FROM {esquema_raw}.{nombre_tabla}
            WHERE {condicion_invalida_inicial};

            -- 3. Stream sobre la tabla RAW (captura cambios futuros)
            CREATE OR REPLACE STREAM STREAMS.STREAM_CLEANSED_{nombre_proyecto}_{nombre_tabla}
            ON TABLE {esquema_raw}.{nombre_tabla};

            -- 4. Task: clasifica cambios futuros de RAW en CLEANSED o CLEANSED_ERRORS
            CREATE OR REPLACE TASK TASKS.TASK_CLEANSED_{nombre_proyecto}_{nombre_tabla}
            WAREHOUSE = COMPUTE_WH
            SCHEDULE = '5 MINUTE'
            WHEN SYSTEM$STREAM_HAS_DATA('STREAMS.STREAM_CLEANSED_{nombre_proyecto}_{nombre_tabla}')
            AS
            BEGIN

                -- A) Filas VALIDAS -> CLEANSED.NombreTabla
                MERGE INTO {esquema_cleansed}.{nombre_tabla} AS target
                USING (
                    SELECT *, METADATA$ACTION AS ACCION_CDC
                    FROM STREAMS.STREAM_CLEANSED_{nombre_proyecto}_{nombre_tabla}
                    WHERE {condicion_valida}
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
                ) AS source
                ON target.{clave_primaria} = source.{clave_primaria}
                WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
                WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
                WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

                -- B) Filas INVALIDAS -> CLEANSED.NombreTabla_ERRORS
                MERGE INTO {esquema_cleansed}.{nombre_tabla}_ERRORS AS target
                USING (
                    SELECT *, METADATA$ACTION AS ACCION_CDC
                    FROM STREAMS.STREAM_CLEANSED_{nombre_proyecto}_{nombre_tabla}
                    WHERE {condicion_invalida}
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
                ) AS source
                ON target.{clave_primaria} = source.{clave_primaria}
                WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
                WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
                WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

            END;

            -- 5. Activamos la Task
            ALTER TASK TASKS.TASK_CLEANSED_{nombre_proyecto}_{nombre_tabla} RESUME;
            """

            conn.execute_string(script_sql)
            print(f"   {nombre_tabla} configurada en CLEANSED.")

        print("Capa CLEANSED automatizada al 100%.")

    except Exception as e:
        print(f"Error en el despliegue CLEANSED: {e}")
        raise

    finally:
        conn.close()
        print("Conexion a Snowflake cerrada de forma segura.")