# raw_cleansed.py
from conexiones import get_snowflake_connection
from reglas_calidad import REGLAS_CALIDAD

def construir_condicion_calidad(reglas, alias=None):
    """
    Traduce el diccionario de reglas a sentencias SQL.
    """
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
            # Manejo de tipos: comillas para strings, sin comillas para números
            # esto lo que hace es revisar si el valor es string o no, y si es string le pone comillas, sino lo deja tal cual para evitar errores de sintaxis SQL
            valores = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in regla["valores"]])
            condiciones.append(f"{col} IN ({valores})")
        elif regla["regla"] == "regex":
            condiciones.append(f"REGEXP_LIKE({col}, '{regla['patron']}')")
        elif regla["regla"] == "range":
            condiciones.append(f"{col} >= {regla['min']} AND {col} <= {regla['max']}")
            
    return " AND ".join(condiciones) if condiciones else "1=1"


def desplegar_capa_cleansed_automatica():
    print("🚀 Iniciando despliegue de capa CLEANSED (Arquitectura de Doble Stream)...")

    conn = get_snowflake_connection()

    try:
        # 1. Detectamos las tablas en RAW que deben subir a CLEANSED
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

            print(f"⚙️ Configurando: {nombre_tabla} | PK: {clave_primaria}")

            # Obtenemos las columnas para construir los MERGE
            cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{esquema_raw}'
                  AND TABLE_NAME   = '{nombre_tabla}'
                ORDER BY ORDINAL_POSITION
            """)
            columnas       = [row[0] for row in cursor.fetchall()]
            columnas_upper = [c.upper() for c in columnas]

            # Determinamos el orden para el CDC (Deduplicación)
            if "FECHA_MODIFICACION" in columnas_upper:
                orden_cdc = "FECHA_MODIFICACION DESC"
            elif "FECHA_REGISTRO" in columnas_upper:
                orden_cdc = "FECHA_REGISTRO DESC"
            else:
                orden_cdc = "_DLT_LOAD_ID DESC"

            update_set  = ", ".join([f"{col} = source.{col}" for col in columnas])
            insert_cols = ", ".join(columnas)
            insert_vals = ", ".join([f"source.{col}" for col in columnas])

            # --- LÓGICA DE CALIDAD ---
            reglas = REGLAS_CALIDAD.get(nombre_tabla_lower, [])

            if reglas:
                cond_valida = construir_condicion_calidad(reglas)
                condicion_valida_inicial   = cond_valida
                # Solución blindada con CASE WHEN para la carga inicial
                condicion_invalida_inicial = f"CASE WHEN {cond_valida} THEN TRUE ELSE FALSE END = FALSE"
                
                #cond_valida_m = construir_condicion_calidad(reglas, alias="source")
                condicion_valida_merge     = cond_valida
                # Solución blindada con CASE WHEN para el MERGE
                condicion_invalida_merge   = f"CASE WHEN {cond_valida} THEN TRUE ELSE FALSE END = FALSE"
                print(f"   ✅ {len(reglas)} reglas detectadas.")
            else:
                condicion_valida_inicial   = "1=1"
                condicion_invalida_inicial = "1=0"
                condicion_valida_merge     = "1=1"
                condicion_invalida_merge   = "1=0"
                print(f"   ⚪ Sin reglas definidas. Todo pasa a CLEANSED.")

            # --- NOMBRES DE OBJETOS ---
            # CORRECCIÓN 2: Dos Streams independientes para que las Tasks no se roben los datos entre sí (CLEANSED vs CLEANSED_ERRORS), 
            # ya que al principio cuando ejecutaba la Task de CLEANSED, me consumía los datos del Stream y la Task de CLEANSED_ERRORS no tenía datos para procesar. 
            nombre_stream     = f"STREAMS.STREAM_CLEANSED_{nombre_proyecto}_{nombre_tabla}"
            nombre_stream_errors = f"STREAMS.STREAM_CLEANSED_{nombre_proyecto}_{nombre_tabla}_ERRORS"
            
            nombre_task       = f"TASKS.TASK_CLEANSED_{nombre_proyecto}_{nombre_tabla}"
            nombre_task_errors   = f"TASKS.TASK_CLEANSED_{nombre_proyecto}_{nombre_tabla}_ERRORS"

            script_sql = f"""
            -- 0. Asegurar Esquemas
            CREATE SCHEMA IF NOT EXISTS {esquema_cleansed};
            CREATE SCHEMA IF NOT EXISTS STREAMS;
            CREATE SCHEMA IF NOT EXISTS TASKS;

            -- 1. Carga Inicial: Datos Válidos
            CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}
            AS SELECT * FROM {esquema_raw}.{nombre_tabla}
            WHERE {condicion_valida_inicial};

            -- 2. Carga Inicial: Datos Inválidos (Cuarentena)
            CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}_ERRORS
            AS SELECT * FROM {esquema_raw}.{nombre_tabla}
            WHERE {condicion_invalida_inicial};

            -- 3. Crear STREAMS Independientes
            CREATE OR REPLACE STREAM {nombre_stream} ON TABLE {esquema_raw}.{nombre_tabla};
            CREATE OR REPLACE STREAM {nombre_stream_errors} ON TABLE {esquema_raw}.{nombre_tabla};

            -- 4a. Task para Filas VÁLIDAS
            CREATE OR REPLACE TASK {nombre_task}
            WAREHOUSE = COMPUTE_WH
            SCHEDULE = '5 MINUTE'
            WHEN SYSTEM$STREAM_HAS_DATA('{nombre_stream}')
            AS
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

            -- 4b. Task para Filas INVÁLIDAS (Cuarentena)
            CREATE OR REPLACE TASK {nombre_task_errors}
            WAREHOUSE = COMPUTE_WH
            SCHEDULE = '5 MINUTE'
            WHEN SYSTEM$STREAM_HAS_DATA('{nombre_stream_errors}')
            AS
            MERGE INTO {esquema_cleansed}.{nombre_tabla}_ERRORS AS target
            USING (
                SELECT *, METADATA$ACTION AS ACCION_CDC
                FROM {nombre_stream_errors}
                WHERE {condicion_invalida_merge}
                QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
            ) AS source
            ON target.{clave_primaria} = source.{clave_primaria}
            WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
            WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
            WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

            -- 5. Activar Tareas
            ALTER TASK {nombre_task} RESUME;
            ALTER TASK {nombre_task_errors} RESUME;
            """

            conn.execute_string(script_sql)
            print(f"   ✅ {nombre_tabla} desplegada correctamente.")

        print("\n🏆 Capa CLEANSED automatizada al 100%. Los datos fluyen hacia Calidad y Cuarentena.")

    except Exception as e:
        print(f"❌ Error en el despliegue CLEANSED: {e}")
        raise

    finally:
        conn.close()
        print("🔌 Conexión cerrada de forma segura.")

if __name__ == "__main__":
    desplegar_capa_cleansed_automatica()