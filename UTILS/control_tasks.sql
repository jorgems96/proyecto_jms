-- control_tasks.sql
-- Define SPs de activacion y suspension de tasks por cada capa del proyecto.
-- Ninguno crea tasks: solo actuan sobre los que ya existen tras el deploy.
-- Activacion [A]: RESUME a todos los tasks (para carga incremental CDC).
-- Suspension [S]: SUSPEND a todos los tasks (para no consumir creditos Snowflake).

-- ============================================================
-- RAW: activa los tasks derivando nombres desde tablas LANDING_*
-- (mismo patron que SP_DEPLOY_RAW: LANDING_X -> RAW_X.TASK_tabla)
-- ============================================================
CREATE OR REPLACE PROCEDURE RAW.SP_ACTIVAR_TASKS()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    v_sql    VARCHAR;
    v_cuenta NUMBER DEFAULT 0;
    cur CURSOR FOR (
        SELECT
            REPLACE(TABLE_SCHEMA, 'LANDING_', 'RAW_') AS raw_schema,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA LIKE 'LANDING_%'
          AND TABLE_TYPE = 'BASE TABLE'
          AND NOT STARTSWITH(UPPER(TABLE_NAME), '_DLT')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    );
BEGIN
    FOR rec IN cur DO
        v_sql := 'ALTER TASK ' || rec.raw_schema || '.TASK_' || rec.TABLE_NAME || ' RESUME';
        EXECUTE IMMEDIATE :v_sql;
        v_cuenta := v_cuenta + 1;
    END FOR;
    RETURN 'RAW tasks activados: ' || v_cuenta;
END;
$$;


-- ============================================================
-- CLEANSED: activa los tasks derivando nombres desde tablas RAW_*
-- (mismo patron que SP_DEPLOY_CLEANSED: RAW_X -> CLEANSED_X.TASK_tabla)
-- ============================================================
CREATE OR REPLACE PROCEDURE CLEANSED.SP_ACTIVAR_TASKS()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    v_sql    VARCHAR;
    v_cuenta NUMBER DEFAULT 0;
    cur CURSOR FOR (
        SELECT
            REPLACE(TABLE_SCHEMA, 'RAW_', 'CLEANSED_') AS cleansed_schema,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA LIKE 'RAW_%'
          AND TABLE_TYPE = 'BASE TABLE'
          AND NOT STARTSWITH(UPPER(TABLE_NAME), '_DLT')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    );
BEGIN
    FOR rec IN cur DO
        v_sql := 'ALTER TASK ' || rec.cleansed_schema || '.TASK_' || rec.TABLE_NAME || ' RESUME';
        EXECUTE IMMEDIATE :v_sql;
        v_cuenta := v_cuenta + 1;
    END FOR;
    RETURN 'CLEANSED tasks activados: ' || v_cuenta;
END;
$$;


-- ============================================================
-- CONFORMED: activa el DAG (hijos primero, ROOT al final)
-- ============================================================
CREATE OR REPLACE PROCEDURE CONFORMED.SP_ACTIVAR_TASKS()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    -- Hijos primero (requerido por Snowflake para Task DAGs)
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_FECHA                     RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_PERFIL_MANTENIMIENTO      RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_PERFIL_ENSAYO             RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_DEPARTAMENTO              RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_UBICACION                 RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_FABRICANTE                RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_MEDICO                    RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_TECNICO                   RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_PACIENTE                  RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_EQUIPO                    RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_ENSAYO                    RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_DIAGNOSTICO               RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_FACT_MANTENIMIENTO_EQUIPOS    RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_FACT_MONITORIZACION_PACIENTES RESUME';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_FACT_ENSAYOS_CLINICOS         RESUME';
    -- ROOT siempre al final
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_CONFORMED_ROOT                RESUME';

    RETURN 'CONFORMED tasks activados: 16';
END;
$$;


-- ============================================================
-- RAW: suspende los tasks derivando nombres desde tablas LANDING_*
-- ============================================================
CREATE OR REPLACE PROCEDURE RAW.SP_SUSPENDER_TASKS()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    v_sql    VARCHAR;
    v_cuenta NUMBER DEFAULT 0;
    cur CURSOR FOR (
        SELECT
            REPLACE(TABLE_SCHEMA, 'LANDING_', 'RAW_') AS raw_schema,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA LIKE 'LANDING_%'
          AND TABLE_TYPE = 'BASE TABLE'
          AND NOT STARTSWITH(UPPER(TABLE_NAME), '_DLT')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    );
BEGIN
    FOR rec IN cur DO
        v_sql := 'ALTER TASK ' || rec.raw_schema || '.TASK_' || rec.TABLE_NAME || ' SUSPEND';
        EXECUTE IMMEDIATE :v_sql;
        v_cuenta := v_cuenta + 1;
    END FOR;
    RETURN 'RAW tasks suspendidos: ' || v_cuenta;
END;
$$;


-- ============================================================
-- CLEANSED: suspende los tasks derivando nombres desde tablas RAW_*
-- ============================================================
CREATE OR REPLACE PROCEDURE CLEANSED.SP_SUSPENDER_TASKS()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    v_sql    VARCHAR;
    v_cuenta NUMBER DEFAULT 0;
    cur CURSOR FOR (
        SELECT
            REPLACE(TABLE_SCHEMA, 'RAW_', 'CLEANSED_') AS cleansed_schema,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA LIKE 'RAW_%'
          AND TABLE_TYPE = 'BASE TABLE'
          AND NOT STARTSWITH(UPPER(TABLE_NAME), '_DLT')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    );
BEGIN
    FOR rec IN cur DO
        v_sql := 'ALTER TASK ' || rec.cleansed_schema || '.TASK_' || rec.TABLE_NAME || ' SUSPEND';
        EXECUTE IMMEDIATE :v_sql;
        v_cuenta := v_cuenta + 1;
    END FOR;
    RETURN 'CLEANSED tasks suspendidos: ' || v_cuenta;
END;
$$;


-- ============================================================
-- CONFORMED: suspende el DAG (ROOT primero, hijos despues)
-- ============================================================
CREATE OR REPLACE PROCEDURE CONFORMED.SP_SUSPENDER_TASKS()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    -- ROOT primero (evita que dispare hijos mientras se suspenden)
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_CONFORMED_ROOT                SUSPEND';
    -- Hijos
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_FECHA                     SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_PERFIL_MANTENIMIENTO      SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_PERFIL_ENSAYO             SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_DEPARTAMENTO              SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_UBICACION                 SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_FABRICANTE                SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_MEDICO                    SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_TECNICO                   SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_PACIENTE                  SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_EQUIPO                    SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_ENSAYO                    SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_DIM_DIAGNOSTICO               SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_FACT_MANTENIMIENTO_EQUIPOS    SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_FACT_MONITORIZACION_PACIENTES SUSPEND';
    EXECUTE IMMEDIATE 'ALTER TASK CONFORMED.TASK_FACT_ENSAYOS_CLINICOS         SUSPEND';

    RETURN 'CONFORMED tasks suspendidos: 16';
END;
$$;
