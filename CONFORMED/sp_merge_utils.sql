-- sp_merge_utils.sql
-- Procedimientos genéricos reutilizables para la carga de dimensiones SCD1 y SCD1+SCD2.
-- Construyen dinámicamente el UPDATE e INSERT a partir de los parámetros y los ejecutan
-- con EXECUTE IMMEDIATE, eliminando la duplicación de código en los ficheros de dimensión.
--
-- DIMENSIONES QUE USAN SP_MERGE_SCD1  (solo SCD1, sin historial):
--   DIM_DIAGNOSTICO, DIM_FABRICANTE, DIM_UBICACION, DIM_ENSAYO
--
-- DIMENSIONES QUE USAN SP_MERGE_SCD1_SCD2  (SCD1 en caliente + SCD2 con historial):
--   DIM_MEDICO, DIM_TECNICO, DIM_PACIENTE, DIM_EQUIPO
--
-- DIMENSIONES NO CUBIERTAS (lógica especial, quedan con SQL propio):
--   DIM_DEPARTAMENTO  — CTE recursiva + subconsulta correlacionada en SET
--   DIM_FECHA         — CREATE OR REPLACE TABLE AS SELECT (generador de fechas)
--   DIM_PERFIL_*      — dimensiones junk sin UPDATE, INSERT via CROSS JOIN

CREATE SCHEMA IF NOT EXISTS CONFORMED;


-- ============================================================
-- SP_MERGE_SCD1
--
--   p_tabla  — tabla destino,  p.ej. 'CONFORMED.DIM_DIAGNOSTICO'
--   p_fuente — SELECT que devuelve p_id + todas las cols SCD1,
--              con aliases ya aplicados si la fuente difiere del spec
--   p_id     — columna clave de negocio, p.ej. 'ID_DIAGNOSTICO'
--   p_cols   — columnas SCD1 separadas por coma (sin espacios)
--
-- Genera y ejecuta:
--   PASO 1 — UPDATE: sobrescribe las cols SCD1 cuando alguna cambia
--   PASO 2 — INSERT: inserta los registros que aún no existen
-- ============================================================
CREATE OR REPLACE PROCEDURE CONFORMED.SP_MERGE_SCD1(
    p_tabla  VARCHAR,
    p_fuente VARCHAR,
    p_id     VARCHAR,
    p_cols   VARCHAR
)
RETURNS STRING
LANGUAGE SQL
AS
DECLARE
    v_arr   ARRAY;
    v_n     INTEGER;
    v_col   VARCHAR;
    v_set   VARCHAR DEFAULT '';
    v_cond  VARCHAR DEFAULT '';
    v_icols VARCHAR DEFAULT '';
    v_ivals VARCHAR DEFAULT '';
    i       INTEGER DEFAULT 0;
    v_sql   VARCHAR;
BEGIN
    v_arr   := STRTOK_TO_ARRAY(p_cols, ',');
    v_n     := ARRAY_SIZE(v_arr);
    v_icols := p_id;
    v_ivals := 's.' || p_id;

    WHILE i < v_n DO
        v_col   := TRIM(GET(v_arr, i)::VARCHAR);
        v_set   := v_set  || IFF(i = 0, '',      ', ')  || 't.' || v_col || ' = s.' || v_col;
        v_cond  := v_cond || IFF(i = 0, '', ' OR ')     || 't.' || v_col || ' IS DISTINCT FROM s.' || v_col;
        v_icols := v_icols || ', ' || v_col;
        v_ivals := v_ivals || ', s.' || v_col;
        i := i + 1;
    END WHILE;

    -- PASO 1: SCD1 — actualizar registros existentes cuando cambia algún atributo
    v_sql := 'UPDATE ' || p_tabla || ' t'
          || ' SET '    || v_set
          || ' FROM ('  || p_fuente || ') s'
          || ' WHERE t.' || p_id || ' = s.' || p_id
          || ' AND ('   || v_cond || ')';
    EXECUTE IMMEDIATE v_sql;

    -- PASO 2: insertar registros nuevos que aún no existen en la dimensión
    v_sql := 'INSERT INTO ' || p_tabla || ' (' || v_icols || ')'
          || ' SELECT '   || v_ivals
          || ' FROM ('    || p_fuente || ') s'
          || ' WHERE NOT EXISTS ('
          || '   SELECT 1 FROM ' || p_tabla || ' t'
          || '   WHERE t.' || p_id || ' = s.' || p_id || ')';
    EXECUTE IMMEDIATE v_sql;

    RETURN 'SP_MERGE_SCD1 OK: ' || p_tabla;
END;


-- ============================================================
-- SP_MERGE_SCD1_SCD2
--
--   p_tabla     — tabla destino
--   p_fuente    — SELECT que devuelve p_id + cols SCD1 + cols SCD2,
--                 con aliases ya aplicados (query único para los 3 pasos)
--   p_id        — columna clave de negocio
--   p_cols_scd1 — cols SCD1 (sobrescritura sin historial), sep. por coma
--   p_cols_scd2 — cols SCD2 (cierran versión y abren nueva), sep. por coma
--                 La tabla destino debe tener FECHA_INICIO, FECHA_FIN, ES_ACTUAL
--
-- Genera y ejecuta:
--   PASO 1 — UPDATE SCD1: sobrescribe cols SCD1 en la versión activa
--   PASO 2 — UPDATE SCD2: cierra versión activa cuando cambia alguna col SCD2
--   PASO 3 — INSERT: abre nueva versión para cerrados en paso 2 + nuevos
-- ============================================================
CREATE OR REPLACE PROCEDURE CONFORMED.SP_MERGE_SCD1_SCD2(
    p_tabla     VARCHAR,
    p_fuente    VARCHAR,
    p_id        VARCHAR,
    p_cols_scd1 VARCHAR,
    p_cols_scd2 VARCHAR
)
RETURNS STRING
LANGUAGE SQL
AS
DECLARE
    v_arr1  ARRAY;
    v_n1    INTEGER;
    v_set1  VARCHAR DEFAULT '';
    v_cond1 VARCHAR DEFAULT '';
    v_arr2  ARRAY;
    v_n2    INTEGER;
    v_cond2 VARCHAR DEFAULT '';
    v_icols VARCHAR DEFAULT '';
    v_ivals VARCHAR DEFAULT '';
    v_col   VARCHAR;
    i       INTEGER DEFAULT 0;
    v_sql   VARCHAR;
BEGIN
    v_icols := p_id;
    v_ivals := 's.' || p_id;

    -- Construir listas para SCD1
    v_arr1 := STRTOK_TO_ARRAY(p_cols_scd1, ',');
    v_n1   := ARRAY_SIZE(v_arr1);
    i      := 0;
    WHILE i < v_n1 DO
        v_col   := TRIM(GET(v_arr1, i)::VARCHAR);
        v_set1  := v_set1  || IFF(i = 0, '',      ', ')  || 't.' || v_col || ' = s.' || v_col;
        v_cond1 := v_cond1 || IFF(i = 0, '', ' OR ')     || 't.' || v_col || ' IS DISTINCT FROM s.' || v_col;
        v_icols := v_icols || ', ' || v_col;
        v_ivals := v_ivals || ', s.' || v_col;
        i := i + 1;
    END WHILE;

    -- Construir condición de cambio para SCD2
    v_arr2 := STRTOK_TO_ARRAY(p_cols_scd2, ',');
    v_n2   := ARRAY_SIZE(v_arr2);
    i      := 0;
    WHILE i < v_n2 DO
        v_col   := TRIM(GET(v_arr2, i)::VARCHAR);
        v_cond2 := v_cond2 || IFF(i = 0, '', ' OR ') || 't.' || v_col || ' IS DISTINCT FROM s.' || v_col;
        v_icols := v_icols || ', ' || v_col;
        v_ivals := v_ivals || ', s.' || v_col;
        i := i + 1;
    END WHILE;

    -- Añadir columnas de control SCD2 al INSERT
    v_icols := v_icols || ', FECHA_INICIO, FECHA_FIN, ES_ACTUAL';
    v_ivals := v_ivals || ', CURRENT_DATE, NULL, TRUE';

    -- PASO 1: SCD1 — actualizar en sitio sin guardar historial
    v_sql := 'UPDATE ' || p_tabla || ' t'
          || ' SET '    || v_set1
          || ' FROM ('  || p_fuente || ') s'
          || ' WHERE t.' || p_id   || ' = s.' || p_id
          || ' AND t.ES_ACTUAL = TRUE'
          || ' AND ('   || v_cond1 || ')';
    EXECUTE IMMEDIATE v_sql;

    -- PASO 2: SCD2 — cerrar versión activa cuando cambia algún atributo SCD2
    v_sql := 'UPDATE ' || p_tabla || ' t'
          || ' SET FECHA_FIN = CURRENT_DATE - 1, ES_ACTUAL = FALSE'
          || ' FROM ('  || p_fuente || ') s'
          || ' WHERE t.' || p_id   || ' = s.' || p_id
          || ' AND t.ES_ACTUAL = TRUE'
          || ' AND ('   || v_cond2 || ')';
    EXECUTE IMMEDIATE v_sql;

    -- PASO 3: INSERT — nueva versión para registros cerrados en paso 2 + nuevos
    v_sql := 'INSERT INTO ' || p_tabla || ' (' || v_icols || ')'
          || ' SELECT '   || v_ivals
          || ' FROM ('    || p_fuente || ') s'
          || ' WHERE NOT EXISTS ('
          || '   SELECT 1 FROM ' || p_tabla || ' t'
          || '   WHERE t.' || p_id || ' = s.' || p_id
          || '     AND t.ES_ACTUAL = TRUE)';
    EXECUTE IMMEDIATE v_sql;

    RETURN 'SP_MERGE_SCD1_SCD2 OK: ' || p_tabla;
END;
