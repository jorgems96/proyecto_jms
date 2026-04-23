# Landing_a_Raw.py
import dlt
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
              AND NOT STARTSWITH(t.TABLE_NAME, '_DLT')
              AND STARTSWITH(c.COLUMN_NAME, 'ID_')
            QUALIFY ROW_NUMBER() OVER (PARTITION BY t.TABLE_NAME ORDER BY c.ORDINAL_POSITION) = 1;
        """
        
        cursor = conn.cursor()
        cursor.execute(query_detective)
        tablas_con_pk = cursor.fetchall()
        
        for esquema_landing, nombre_tabla, clave_primaria in tablas_con_pk:
            esquema_raw = esquema_landing.replace('LANDING_', 'RAW_')
            nombre_proyecto = esquema_landing.replace('LANDING_', '')
            
            print(f"⚙️ Configurando: {nombre_tabla} | PK Detectada: {clave_primaria}")
            
            # --- NUEVO: Extraemos la lista exacta de columnas de la tabla actual ---
            cursor.execute(f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = '{esquema_landing}' 
                  AND TABLE_NAME = '{nombre_tabla}'
            """)
            columnas = [row[0] for row in cursor.fetchall()]
            
            # --- NUEVO: Lógica simple para decidir por qué campo ordenar ---
            columnas_upper = [c.upper() for c in columnas]
            
            if "FECHA_MODIFICACION" in columnas_upper:
                orden_cdc = "FECHA_MODIFICACION DESC"
            elif "FECHA_REGISTRO" in columnas_upper:
                orden_cdc = "FECHA_REGISTRO DESC"
            else:
                # Un salvavidas por si alguna tabla rara no tiene ninguna de las dos, 
                # pues puedo recurrir al ID como proxy de orden de llegada del dato a landing(asumiendo que es autoincremental)
                orden_cdc = "_dlt_load_id DESC" 
            # ---------------------------------------------------------------

            # Python construye las listas dinámicamente: "col1 = source.col1, col2 = source.col2..."
            update_set = ", ".join([f"{col} = source.{col}" for col in columnas])
            insert_cols = ", ".join(columnas)
            insert_vals = ", ".join([f"source.{col}" for col in columnas])

            # BORRADO LOGICO: añado logica de borrado si existe la columna _is_deleted en origen
            clausula_delete = "WHEN MATCHED AND source._is_deleted = TRUE THEN DELETE" if "_is_deleted" in [c.lower() for c in columnas] else ""

            script_sql = f"""
            -- 0. Nos aseguramos de que todos los esquemas existen
            CREATE SCHEMA IF NOT EXISTS {esquema_raw};
            CREATE SCHEMA IF NOT EXISTS STREAMS;
            CREATE SCHEMA IF NOT EXISTS TASKS;

            -- 1. Creamos la tabla RAW (Carga inicial deduplicada usando orden_cdc)
            CREATE TABLE IF NOT EXISTS {esquema_raw}.{nombre_tabla} 
            -- cluster by ({clave_primaria}) # Opcional: Si queremos mejorar el rendimiento de las consultas en RAW, 
            -- podríamos ORDENAR por la clave primaria, aunque esto depende del tamaño de la tabla 
            --y del patrón de consultas esperado. Para tablas pequeñas o medianas, no es estrictamente necesario. 
            --Para tablas muy grandes, podría ser un gran beneficio. 
            --Se puede probar con y sin clusterización para ver el impacto en el rendimiento.
            AS 
            SELECT * FROM {esquema_landing}.{nombre_tabla}
            -- Aquí uso la lógica de orden_cdc para quedarme solo con la fila más reciente por clave primaria, 
            --evitando así enviar duplicados hacia la capa RAW en caso de que la tabla de LANDING ya tenga datos
             -- antes de crear el STREAM y la TASK.
            QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1;
              

            -- 2. Creamos el STREAM dentro del esquema STREAMS
            CREATE OR REPLACE STREAM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla} 
            ON TABLE {esquema_landing}.{nombre_tabla};

            -- 3. Creamos la TASK dentro del esquema TASKS
            CREATE OR REPLACE TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla}
            WAREHOUSE = COMPUTE_WH
            SCHEDULE = '5 MINUTE'
            WHEN SYSTEM$STREAM_HAS_DATA('STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}')
            AS
            MERGE INTO {esquema_raw}.{nombre_tabla} AS target
            USING (
                SELECT * EXCLUDE (METADATA$ACTION, METADATA$ISUPDATE, METADATA$ROW_ID)
                FROM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}
                QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
            ) AS source
            ON target.{clave_primaria} = source.{clave_primaria}
            {clausula_delete}
            WHEN MATCHED THEN UPDATE SET {update_set}
            WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals});

            -- 4. Activamos la TASK apuntando a su esquema correcto
            ALTER TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla} RESUME;
            """
            
            conn.execute_string(script_sql)
        
        print("✅ Capa RAW automatizada al 100%. Mantenimiento cero conseguido.")

    except Exception as e:
        print(f"❌ Error en el despliegue RAW: {e}")
        raise 

    finally:
        conn.close()
        print("🔌 Conexión a Snowflake cerrada de forma segura.")




#BORRADO LOGICO Y FISICO: Ahora tu código es "híbrido" (BORRADO LOGICO Y FISICO). Si borras la fila físicamente en Landing, 
# la borra en Raw. Si solo la marcas como borrada lógicamente (si existe la columna), 
# también la borra.

        # script_sql = f"""
        #     -- 0. Asegurar esquemas
        #     CREATE SCHEMA IF NOT EXISTS {esquema_raw};
        #     CREATE SCHEMA IF NOT EXISTS STREAMS;
        #     CREATE SCHEMA IF NOT EXISTS TASKS;

        #     -- 1. Tabla RAW
        #     CREATE TABLE IF NOT EXISTS {esquema_raw}.{nombre_tabla} 
        #     AS 
        #     SELECT * FROM {esquema_landing}.{nombre_tabla}
        #     QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1;

        #     -- 2. STREAM
        #     CREATE OR REPLACE STREAM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla} 
        #     ON TABLE {esquema_landing}.{nombre_tabla};

        #     -- 3. TASK con detección de Hard Delete
        #     CREATE OR REPLACE TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla}
        #     WAREHOUSE = COMPUTE_WH
        #     SCHEDULE = '5 MINUTE'
        #     WHEN SYSTEM$STREAM_HAS_DATA('STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}')
        #     AS
        #     MERGE INTO {esquema_raw}.{nombre_tabla} AS target
        #     USING (
        #         -- Importante: Mantenemos METADATA$ACTION para saber si es un borrado físico
        #         SELECT *, METADATA$ACTION AS ACCION_CDC
        #         FROM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}
        #         QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
        #     ) AS source
        #     ON target.{clave_primaria} = source.{clave_primaria}
            
        #     -- SI LA ACCIÓN ES DELETE O TIENE EL FLAG DE BORRADO -> BORRAMOS EN RAW
        #     WHEN MATCHED AND (source.ACCION_CDC = 'DELETE' {f"OR source._is_deleted = TRUE" if "_is_deleted" in [c.lower() for c in columnas] else ""}) 
        #         THEN DELETE
                
        #     -- SI COINCIDE Y NO ES BORRADO -> ACTUALIZAMOS
        #     WHEN MATCHED AND source.ACCION_CDC = 'INSERT' 
        #         THEN UPDATE SET {update_set}
                
        #     -- SI NO EXISTE -> INSERTAMOS
        #     WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' 
        #         THEN INSERT ({insert_cols}) VALUES ({insert_vals});

        #     -- 4. Activar
        #     ALTER TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla} RESUME;
        #     """



#BORRADO FISICO 

# ... (código de arriba igual: detección de columnas y orden_cdc) ...
            # update_set = ", ".join([f"{col} = source.{col}" for col in columnas])
            # insert_cols = ", ".join(columnas)
            # insert_vals = ", ".join([f"source.{col}" for col in columnas])

            # # ¡HEMOS ELIMINADO LA VARIABLE clausula_delete PORQUE NO TIENES BORRADO LÓGICO!

            # script_sql = f"""
            # -- 0. Nos aseguramos de que todos los esquemas existen
            # CREATE SCHEMA IF NOT EXISTS {esquema_raw};
            # CREATE SCHEMA IF NOT EXISTS STREAMS;
            # CREATE SCHEMA IF NOT EXISTS TASKS;

            # -- 1. Creamos la tabla RAW (Carga inicial deduplicada usando orden_cdc)
            # CREATE TABLE IF NOT EXISTS {esquema_raw}.{nombre_tabla} 
            # AS 
            # SELECT * FROM {esquema_landing}.{nombre_tabla}
            # QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1;

            # -- 2. Creamos el STREAM dentro del esquema STREAMS
            # CREATE OR REPLACE STREAM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla} 
            # ON TABLE {esquema_landing}.{nombre_tabla};

            # -- 3. Creamos la TASK dentro del esquema TASKS
            # CREATE OR REPLACE TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla}
            # WAREHOUSE = COMPUTE_WH
            # SCHEDULE = '5 MINUTE'
            # WHEN SYSTEM$STREAM_HAS_DATA('STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}')
            # AS
            # MERGE INTO {esquema_raw}.{nombre_tabla} AS target
            # USING (
            #     -- Mantenemos METADATA$ACTION para saber si Snowflake detectó un DELETE físico en Landing
            #     SELECT *, METADATA$ACTION AS ACCION_CDC
            #     FROM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}
            #     QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
            # ) AS source
            # ON target.{clave_primaria} = source.{clave_primaria}
            
            # -- SI EL STREAM DICE QUE FUE UN BORRADO FÍSICO -> BORRAMOS EN RAW
            # WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
            
            # -- SI COINCIDE Y ES UN DATO NUEVO/ACTUALIZADO -> ACTUALIZAMOS EN RAW
            # WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
            
            # -- SI NO EXISTE EN RAW -> INSERTAMOS
            # WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

            # -- 4. Activamos la TASK apuntando a su esquema correcto
            # ALTER TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla} RESUME;
            # """