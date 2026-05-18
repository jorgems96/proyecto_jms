-- sp_deploy_raw.sql


--crea esquemas, tablas, streams y tasks RAW
-- automaticamente a partir de las tablas LANDING_ detectadas en INFORMATION_SCHEMA.


CREATE OR REPLACE PROCEDURE RAW.SP_DEPLOY_RAW()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    v_orden_cdc        VARCHAR;
    v_borrado_clausula VARCHAR;
    v_sql              VARCHAR;
    v_esquema_landing  VARCHAR;
    v_esquema_raw      VARCHAR;
    v_table_name       VARCHAR;
    v_clave_primaria   VARCHAR;
    v_insert_cols      VARCHAR;
    v_update_set       VARCHAR;
    v_insert_vals      VARCHAR;
    v_cdc_priority     NUMBER;
    v_col_borrado      VARCHAR;
    cur CURSOR FOR (
        SELECT
            t.TABLE_SCHEMA                               AS esquema_landing,
            REPLACE(t.TABLE_SCHEMA, 'LANDING_', 'RAW_') AS esquema_raw,
            t.TABLE_NAME,
            MIN(CASE WHEN STARTSWITH(UPPER(c.COLUMN_NAME), 'ID_') THEN c.COLUMN_NAME END) AS clave_primaria,
            LISTAGG(
                CASE WHEN NOT STARTSWITH(UPPER(c.COLUMN_NAME), '_DLT') THEN c.COLUMN_NAME       END, ', '
            ) WITHIN GROUP (ORDER BY c.ORDINAL_POSITION)                                  AS insert_cols,
            LISTAGG(
                CASE WHEN NOT STARTSWITH(UPPER(c.COLUMN_NAME), '_DLT')
                     THEN c.COLUMN_NAME || ' = source.' || c.COLUMN_NAME                 END, ', '
            ) WITHIN GROUP (ORDER BY c.ORDINAL_POSITION)                                  AS update_set,
            LISTAGG(
                CASE WHEN NOT STARTSWITH(UPPER(c.COLUMN_NAME), '_DLT')
                     THEN 'source.' || c.COLUMN_NAME                                      END, ', '
            ) WITHIN GROUP (ORDER BY c.ORDINAL_POSITION)                                  AS insert_vals,
            MAX(IFF(UPPER(c.COLUMN_NAME) = 'FECHA_MODIFICACION', 2,
                IFF(UPPER(c.COLUMN_NAME) = 'FECHA_REGISTRO',     1, 0)))                 AS cdc_priority,
            MAX(CASE WHEN UPPER(c.COLUMN_NAME) IN ('_IS_DELETED', '_DLT_DELETED', 'IS_DELETED', 'BORRADO')
                     THEN c.COLUMN_NAME END)                                              AS col_borrado
        FROM INFORMATION_SCHEMA.TABLES t
        JOIN INFORMATION_SCHEMA.COLUMNS c
          ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
         AND c.TABLE_NAME   = t.TABLE_NAME
        WHERE t.TABLE_SCHEMA LIKE 'LANDING_%'
          AND t.TABLE_TYPE  = 'BASE TABLE'
          AND NOT STARTSWITH(UPPER(t.TABLE_NAME), '_DLT')
        GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME
        HAVING MIN(CASE WHEN STARTSWITH(UPPER(c.COLUMN_NAME), 'ID_') THEN c.COLUMN_NAME END) IS NOT NULL
    );
BEGIN
    FOR rec IN cur DO

        v_esquema_landing := rec.esquema_landing;
        v_esquema_raw     := rec.esquema_raw;
        v_table_name      := rec.TABLE_NAME;
        v_clave_primaria  := rec.clave_primaria;
        v_insert_cols     := rec.insert_cols;
        v_update_set      := rec.update_set;
        v_insert_vals     := rec.insert_vals;
        v_cdc_priority    := rec.cdc_priority;
        v_col_borrado     := rec.col_borrado;

        -- Columna de orden para deduplicacion CDC
        IF (v_cdc_priority = 2) THEN
            v_orden_cdc := 'FECHA_MODIFICACION DESC';
        ELSEIF (v_cdc_priority = 1) THEN
            v_orden_cdc := 'FECHA_REGISTRO DESC';
        ELSE
            v_orden_cdc := '_DLT_LOAD_ID DESC';
        END IF;

        -- Clausula de borrado logico (cadena vacia si no aplica)
        IF (v_col_borrado IS NOT NULL) THEN
            v_borrado_clausula :=
                ' WHEN MATCHED AND source.' || v_col_borrado || ' = TRUE THEN DELETE';
        ELSE
            v_borrado_clausula := '';
        END IF;

        -- 1. Esquema RAW
        v_sql := 'CREATE SCHEMA IF NOT EXISTS ' || v_esquema_raw;
        EXECUTE IMMEDIATE :v_sql;

        -- 2. Tabla RAW: carga inicial completa, sin columnas DLT
        --    Sin QUALIFY: en una carga inicial fresh no hay duplicados en LANDING.
        --    La deduplicacion CDC solo se necesita en los streams (step 4, TASK).
        v_sql :=
            'CREATE TABLE IF NOT EXISTS ' || v_esquema_raw || '.' || v_table_name
            || ' AS SELECT * EXCLUDE (_DLT_LOAD_ID, _DLT_ID)'
            || ' FROM '   || v_esquema_landing || '.' || v_table_name;
        EXECUTE IMMEDIATE :v_sql;

        -- 3. Stream sobre la tabla LANDING (captura cambios incrementales)
        v_sql :=
            'CREATE STREAM IF NOT EXISTS ' || v_esquema_raw || '.STREAM_' || v_table_name
            || ' ON TABLE ' || v_esquema_landing || '.' || v_table_name;
        EXECUTE IMMEDIATE :v_sql;

        -- 4. Task con MERGE incremental
        v_sql :=
            'CREATE OR REPLACE TASK ' || v_esquema_raw || '.TASK_' || v_table_name
            || ' WAREHOUSE = COMPUTE_WH'
            || ' SCHEDULE = ''5 MINUTE'''
            || ' WHEN SYSTEM$STREAM_HAS_DATA(''' || v_esquema_raw || '.STREAM_' || v_table_name || ''')'
            || ' AS'
            || ' MERGE INTO ' || v_esquema_raw || '.' || v_table_name || ' AS target'
            || ' USING ('
            || '   SELECT *, METADATA$ACTION AS ACCION_CDC'
            || '   FROM '  || v_esquema_raw || '.STREAM_' || v_table_name
            || '   QUALIFY ROW_NUMBER() OVER (PARTITION BY ' || v_clave_primaria
            || '   ORDER BY ' || v_orden_cdc || ') = 1'
            || ' ) AS source'
            || ' ON target.' || v_clave_primaria || ' = source.' || v_clave_primaria
            || ' WHEN MATCHED AND source.ACCION_CDC = ''DELETE'' THEN DELETE'
            || v_borrado_clausula
            || ' WHEN MATCHED AND source.ACCION_CDC = ''INSERT'' THEN UPDATE SET ' || v_update_set
            || ' WHEN NOT MATCHED AND source.ACCION_CDC = ''INSERT'''
            || ' THEN INSERT (' || v_insert_cols || ') VALUES (' || v_insert_vals || ')';
        EXECUTE IMMEDIATE :v_sql;

        -- 5. Task creado como SUSPENDED por defecto en Snowflake.

    END FOR;

    RETURN 'SP_DEPLOY_RAW completado correctamente.';
END;
$$;

-- Ejecutar el despliegue completo de la capa RAW:
-- CALL RAW.SP_DEPLOY_RAW();
