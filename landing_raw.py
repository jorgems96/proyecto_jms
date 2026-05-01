
#import dlt
from conexiones import get_snowflake_connection

def desplegar_capa_raw_automatica():
    print("Iniciando escaneo de LANDING y detectando Claves Primarias...")
    
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
            WHERE t.TABLE_SCHEMA LIKE 'LANDING_%' 
              AND t.TABLE_TYPE = 'BASE TABLE'
              AND NOT STARTSWITH(t.TABLE_NAME, '_DLT') -- Excluir tablas de DLT
              AND STARTSWITH(c.COLUMN_NAME, 'ID_') -- Asumimos que las PK empiezan con 'ID_'
            QUALIFY ROW_NUMBER() OVER (PARTITION BY t.TABLE_NAME ORDER BY c.ORDINAL_POSITION) = 1;
        """
        
        cursor = conn.cursor()
        cursor.execute(query_detective)
        tablas_con_pk = cursor.fetchall()
        
        for esquema_landing, nombre_tabla, clave_primaria in tablas_con_pk:
            esquema_raw = esquema_landing.replace('LANDING_', 'RAW_')
            nombre_proyecto = esquema_landing.replace('LANDING_', '')
            
            print(f"[CONFIG] Configurando: {nombre_tabla} | PK Detectada: {clave_primaria}")
            
            cursor.execute(f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = '{esquema_landing}' 
                  AND TABLE_NAME = '{nombre_tabla}'
            """)
            columnas = [row[0] for row in cursor.fetchall()]
            columnas_upper = [c.upper() for c in columnas]
            
            #Modificar, en CLEANSED entran todas las filas
            #no funciona por fecha de modificacion ni registros DLT
            if "FECHA_MODIFICACION" in columnas_upper:
                orden_cdc = "FECHA_MODIFICACION DESC"
            elif "FECHA_REGISTRO" in columnas_upper:
                orden_cdc = "FECHA_REGISTRO DESC"
            else:
                orden_cdc = "_dlt_load_id DESC" 

            # Generar las columnas
            update_set = ", ".join([f"{col} = source.{col}" for col in columnas])
            insert_cols = ", ".join(columnas)
            insert_vals = ", ".join([f"source.{col}" for col in columnas])

            # BORRADO ( DELETE )  
            # Buscamos si la tabla tiene alguna columna típica que indique borrado
            posibles_nombres_borrado = ["_IS_DELETED", "_DLT_DELETED", "IS_DELETED", "BORRADO"]
            col_borrado = next((c for c in columnas_upper if c in posibles_nombres_borrado), None)

            if col_borrado:
                clausula_borrado_logico = f"WHEN MATCHED AND source.{col_borrado} = TRUE THEN DELETE"
                print(f"   [BORRADO LOGICO] Columna detectada: {col_borrado}")
            else:
                clausula_borrado_logico = "-- No aplica borrado lógico: No se detectó columna indicadora."
            # ------------------------------------------------------------------------

            script_sql = f"""
            -- Comprobacion de esquemas
            CREATE SCHEMA IF NOT EXISTS {esquema_raw};
            CREATE SCHEMA IF NOT EXISTS STREAMS;
            CREATE SCHEMA IF NOT EXISTS TASKS;

            -- Crear las tablas RAW 
            CREATE TABLE IF NOT EXISTS {esquema_raw}.{nombre_tabla} 
            --para ordenar las filas por la clave primaria y optimizar las consultas posteriores en raw, pero gastaria mucha computacion.
            -- CLUSTER BY ({clave_primaria})  
            AS 
            SELECT * FROM {esquema_landing}.{nombre_tabla}
            QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1;

            -- Creacion del STREAM dentro del esquema STREAMS
            CREATE OR REPLACE STREAM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla} 
            ON TABLE {esquema_landing}.{nombre_tabla};

            --Creacion de la TASK dentro del esquema TASKS
            CREATE OR REPLACE TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla}
            WAREHOUSE = COMPUTE_WH
            SCHEDULE = '5 MINUTE'
            WHEN SYSTEM$STREAM_HAS_DATA('STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}')
            AS
            MERGE INTO {esquema_raw}.{nombre_tabla} AS target
            USING (
                SELECT *, METADATA$ACTION AS ACCION_CDC
                FROM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}
                QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
            ) AS source
            ON target.{clave_primaria} = source.{clave_primaria}
            
            --Para  BORRADO FÍSICO (delete manual): Si el stream detecta una eliminación directa
            WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
            
            --Para BORRADO LÓGICO (no siempre tiene columna): Si la tabla tiene campo de borrado y viene a TRUE
            {clausula_borrado_logico}
            
            --Para ACTUALIZACIÓN (update): Si la fila ya existe y trae datos nuevos
            WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
            
            --Para INSERCIÓN (insert): Si la fila es completamente nueva
            WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

            --Activo la TASK apuntando al esquema correspondiente 
            ALTER TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla} RESUME;
            """
            
            conn.execute_string(script_sql)
        
        print(" Capa RAW automatizada al 100%. Mantenimiento cero conseguido.")

    except Exception as e:
        print(f" Error en el despliegue RAW: {e}")
        raise 

    finally:
        conn.close()
        print(" Conexión a Snowflake cerrada de forma segura.")