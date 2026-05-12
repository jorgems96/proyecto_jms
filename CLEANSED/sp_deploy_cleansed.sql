-- sp_deploy_cleansed.sql
-- Sustituye a raw_cleansed.py: crea esquemas, tablas, tablas de errores,
-- streams y tasks CLEANSED automaticamente a partir de las tablas RAW_.
--
-- Prerequisito: ejecutar reglas_calidad.sql antes de llamar a este SP,
-- ya que lee CLEANSED.REGLAS_CALIDAD para construir las condiciones de calidad.

CREATE OR REPLACE PROCEDURE CLEANSED.SP_DEPLOY_CLEANSED()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    v_orden_cdc          VARCHAR;
    v_condicion_valida   VARCHAR;
    v_condicion_invalida VARCHAR;
    v_sql                VARCHAR;
    v_esquema_raw        VARCHAR;
    v_esquema_cleansed   VARCHAR;
    v_table_name         VARCHAR;
    v_clave_primaria     VARCHAR;
    v_insert_cols        VARCHAR;
    v_update_set         VARCHAR;
    v_insert_vals        VARCHAR;
    v_cdc_priority       NUMBER;
    cur CURSOR FOR (
        SELECT
            ca.TABLE_SCHEMA                                AS esquema_raw,
            REPLACE(ca.TABLE_SCHEMA, 'RAW_', 'CLEANSED_') AS esquema_cleansed,
            ca.TABLE_NAME,
            ca.clave_primaria,
            ca.insert_cols,
            ca.update_set,
            ca.insert_vals,
            ca.cdc_priority,
            COALESCE(r.condicion_valida, '1=1')            AS condicion_valida,
            CASE WHEN r.condicion_valida IS NULL THEN '1=0'
                 ELSE 'CASE WHEN ' || r.condicion_valida || ' THEN TRUE ELSE FALSE END = FALSE'
            END                                            AS condicion_invalida
        FROM (
            SELECT
                t.TABLE_SCHEMA,
                t.TABLE_NAME,
                MIN(CASE WHEN STARTSWITH(UPPER(c.COLUMN_NAME), 'ID_') THEN c.COLUMN_NAME END) AS clave_primaria,
                LISTAGG(c.COLUMN_NAME, ', ')
                    WITHIN GROUP (ORDER BY c.ORDINAL_POSITION)                        AS insert_cols,
                LISTAGG(c.COLUMN_NAME || ' = source.' || c.COLUMN_NAME, ', ')
                    WITHIN GROUP (ORDER BY c.ORDINAL_POSITION)                        AS update_set,
                LISTAGG('source.' || c.COLUMN_NAME, ', ')
                    WITHIN GROUP (ORDER BY c.ORDINAL_POSITION)                        AS insert_vals,
                MAX(IFF(UPPER(c.COLUMN_NAME) = 'FECHA_MODIFICACION', 2,
                    IFF(UPPER(c.COLUMN_NAME) = 'FECHA_REGISTRO',     1, 0)))          AS cdc_priority
            FROM INFORMATION_SCHEMA.TABLES t
            JOIN INFORMATION_SCHEMA.COLUMNS c
              ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
             AND c.TABLE_NAME   = t.TABLE_NAME
            WHERE t.TABLE_SCHEMA LIKE 'RAW_%'
              AND t.TABLE_TYPE  = 'BASE TABLE'
              AND NOT STARTSWITH(UPPER(t.TABLE_NAME), '_DLT')
            GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME
            HAVING MIN(CASE WHEN STARTSWITH(UPPER(c.COLUMN_NAME), 'ID_') THEN c.COLUMN_NAME END) IS NOT NULL
        ) ca
        LEFT JOIN (
            SELECT
                NOMBRE_TABLA,
                LISTAGG(CONDICION, ' AND ')
                    WITHIN GROUP (ORDER BY COLUMNA)                                   AS condicion_valida
            FROM CLEANSED.REGLAS_CALIDAD
            GROUP BY NOMBRE_TABLA
        ) r ON LOWER(ca.TABLE_NAME) = r.NOMBRE_TABLA
    );
BEGIN
    FOR rec IN cur DO

        v_esquema_raw      := rec.esquema_raw;
        v_esquema_cleansed := rec.esquema_cleansed;
        v_table_name       := rec.TABLE_NAME;
        v_clave_primaria   := rec.clave_primaria;
        v_insert_cols      := rec.insert_cols;
        v_update_set       := rec.update_set;
        v_insert_vals      := rec.insert_vals;
        v_cdc_priority     := rec.cdc_priority;
        v_condicion_valida   := rec.condicion_valida;
        v_condicion_invalida := rec.condicion_invalida;

        -- Columna de orden para deduplicacion CDC
        -- Fallback: clave primaria (tablas RAW no tienen _DLT_LOAD_ID)
        IF (v_cdc_priority = 2) THEN
            v_orden_cdc := 'FECHA_MODIFICACION DESC';
        ELSEIF (v_cdc_priority = 1) THEN
            v_orden_cdc := 'FECHA_REGISTRO DESC';
        ELSE
            v_orden_cdc := v_clave_primaria;
        END IF;

        -- 1. Esquema CLEANSED_*
        v_sql := 'CREATE SCHEMA IF NOT EXISTS ' || v_esquema_cleansed;
        EXECUTE IMMEDIATE :v_sql;

        -- 2. Tabla CLEANSED con filas validas (carga inicial)
        v_sql :=
            'CREATE TABLE IF NOT EXISTS ' || v_esquema_cleansed || '.' || v_table_name
            || ' AS SELECT * FROM ' || v_esquema_raw || '.' || v_table_name
            || ' WHERE ' || v_condicion_valida;
        EXECUTE IMMEDIATE :v_sql;

        -- 3. Tabla CLEANSED_ERRORS con filas invalidas (carga inicial)
        v_sql :=
            'CREATE TABLE IF NOT EXISTS ' || v_esquema_cleansed || '.' || v_table_name || '_ERRORS'
            || ' AS SELECT * FROM ' || v_esquema_raw || '.' || v_table_name
            || ' WHERE ' || v_condicion_invalida;
        EXECUTE IMMEDIATE :v_sql;

        -- 4. Stream en esquema CLEANSED sobre tabla RAW (captura incrementales)
        v_sql :=
            'CREATE STREAM IF NOT EXISTS ' || v_esquema_cleansed || '.STREAM_' || v_table_name
            || ' ON TABLE ' || v_esquema_raw || '.' || v_table_name;
        EXECUTE IMMEDIATE :v_sql;

        -- 5. Task con dos MERGEs en transaccion explicita
        --    (ambos MERGEs leen el mismo snapshot del stream)
        v_sql :=
            'CREATE OR REPLACE TASK ' || v_esquema_cleansed || '.TASK_' || v_table_name
            || ' WAREHOUSE = COMPUTE_WH'
            || ' SCHEDULE = ''5 MINUTE'''
            || ' WHEN SYSTEM$STREAM_HAS_DATA(''' || v_esquema_cleansed || '.STREAM_' || v_table_name || ''')'
            || ' AS BEGIN'
            || '   BEGIN TRANSACTION;'

            -- MERGE filas validas → tabla CLEANSED
            || '   MERGE INTO ' || v_esquema_cleansed || '.' || v_table_name || ' AS target'
            || '   USING ('
            || '     SELECT *, METADATA$ACTION AS ACCION_CDC'
            || '     FROM '   || v_esquema_cleansed || '.STREAM_' || v_table_name
            || '     WHERE '  || v_condicion_valida
            || '     QUALIFY ROW_NUMBER() OVER (PARTITION BY ' || v_clave_primaria
            || '     ORDER BY ' || v_orden_cdc || ') = 1'
            || '   ) AS source'
            || '   ON target.' || v_clave_primaria || ' = source.' || v_clave_primaria
            || '   WHEN MATCHED AND source.ACCION_CDC = ''DELETE'' THEN DELETE'
            || '   WHEN MATCHED AND source.ACCION_CDC = ''INSERT'' THEN UPDATE SET ' || v_update_set
            || '   WHEN NOT MATCHED AND source.ACCION_CDC = ''INSERT'''
            || '   THEN INSERT (' || v_insert_cols || ') VALUES (' || v_insert_vals || ');'

            -- MERGE filas invalidas → tabla ERRORS
            || '   MERGE INTO ' || v_esquema_cleansed || '.' || v_table_name || '_ERRORS AS target'
            || '   USING ('
            || '     SELECT *, METADATA$ACTION AS ACCION_CDC'
            || '     FROM '   || v_esquema_cleansed || '.STREAM_' || v_table_name
            || '     WHERE '  || v_condicion_invalida
            || '     QUALIFY ROW_NUMBER() OVER (PARTITION BY ' || v_clave_primaria
            || '     ORDER BY ' || v_orden_cdc || ') = 1'
            || '   ) AS source'
            || '   ON target.' || v_clave_primaria || ' = source.' || v_clave_primaria
            || '   WHEN MATCHED AND source.ACCION_CDC = ''DELETE'' THEN DELETE'
            || '   WHEN MATCHED AND source.ACCION_CDC = ''INSERT'' THEN UPDATE SET ' || v_update_set
            || '   WHEN NOT MATCHED AND source.ACCION_CDC = ''INSERT'''
            || '   THEN INSERT (' || v_insert_cols || ') VALUES (' || v_insert_vals || ');'

            || '   COMMIT;'
            || ' END';
        EXECUTE IMMEDIATE :v_sql;

        -- 6. Task creado como SUSPENDED por defecto en Snowflake.

    END FOR;

    RETURN 'SP_DEPLOY_CLEANSED completado correctamente.';
END;
$$;

-- Orden de ejecucion:
--   1. CALL RAW.SP_DEPLOY_RAW()
--   2. Ejecutar reglas_calidad.sql
--   3. CALL CLEANSED.SP_DEPLOY_CLEANSED()
