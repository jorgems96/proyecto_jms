-- dimension_medico.sql
-- Dimension SCD1/SCD2 de medicos
-- SCD1: Nombre, Apellidos, Numero_Colegiado, Telefono, Email
-- SCD2: Especialidad, Departamento
-- Fuente: CLEANSED_MEDICARE.MEDICOS
--
-- Nota de nomenclatura:
-- APELLIDO1 || ' ' || APELLIDO2     → APELLIDOS
-- ESPECIALIDADES.NOMBRE_ESPECIALIDAD → ESPECIALIDAD  (JOIN por ID_ESPECIALIDAD)
-- DEPARTAMENTOS.NOMBRE_DEPARTAMENTO  → DEPARTAMENTO  (JOIN por CODIGO_DEPARTAMENTO)


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_MEDICO (
    SK_MEDICO          NUMBER        NOT NULL AUTOINCREMENT PRIMARY KEY,
    ID_MEDICO          NUMBER        NOT NULL,
    NOMBRE             VARCHAR(100)  NOT NULL,
    APELLIDOS          VARCHAR(200)  NOT NULL,
    NUMERO_COLEGIADO   VARCHAR(50)   NOT NULL,
    TELEFONO           VARCHAR(50),
    EMAIL              VARCHAR(100),
    ESPECIALIDAD       VARCHAR(200)  NOT NULL,  -- SCD2
    DEPARTAMENTO       VARCHAR(200),            -- SCD2
    FECHA_INICIO       DATE          NOT NULL,
    FECHA_FIN          DATE,
    ES_ACTUAL          BOOLEAN       NOT NULL   DEFAULT TRUE
);


-- ============================================================
-- PASO 1: SCD1 — actualizar en sitio sin guardar historial
-- ============================================================
UPDATE CONFORMED.DIM_MEDICO t
SET
    NOMBRE           = s.NOMBRE,
    APELLIDOS        = s.APELLIDOS,
    NUMERO_COLEGIADO = s.NUMERO_COLEGIADO,
    TELEFONO         = s.TELEFONO,
    EMAIL            = s.EMAIL
FROM (
    SELECT
        m.ID_MEDICO,
        m.NOMBRE,
        m.APELLIDO1 || ' ' || m.APELLIDO2  AS APELLIDOS,
        m.NUMERO_COLEGIADO,
        m.TELEFONO,
        m.EMAIL
    FROM CLEANSED_MEDICARE.MEDICOS m
) s
WHERE t.ID_MEDICO = s.ID_MEDICO
  AND t.ES_ACTUAL = TRUE
  AND (
      t.NOMBRE           IS DISTINCT FROM s.NOMBRE           OR
      t.APELLIDOS        IS DISTINCT FROM s.APELLIDOS        OR
      t.NUMERO_COLEGIADO IS DISTINCT FROM s.NUMERO_COLEGIADO OR
      t.TELEFONO         IS DISTINCT FROM s.TELEFONO         OR
      t.EMAIL            IS DISTINCT FROM s.EMAIL
  );


-- ============================================================
-- PASO 2: SCD2 — cerrar version actual cuando cambia
--         Especialidad o Departamento
-- ============================================================
UPDATE CONFORMED.DIM_MEDICO t
SET
    FECHA_FIN = CURRENT_DATE - 1,
    ES_ACTUAL = FALSE
FROM (
    SELECT
        m.ID_MEDICO,
        esp.NOMBRE_ESPECIALIDAD        AS ESPECIALIDAD,
        dep.NOMBRE_DEPARTAMENTO        AS DEPARTAMENTO
    FROM CLEANSED_MEDICARE.MEDICOS m
    LEFT JOIN CLEANSED_MEDICARE.ESPECIALIDADES esp ON esp.ID_ESPECIALIDAD     = m.ID_ESPECIALIDAD
    LEFT JOIN CLEANSED_MEDICARE.DEPARTAMENTOS  dep ON dep.CODIGO_DEPARTAMENTO = m.CODIGO_DEPARTAMENTO
) s
WHERE t.ID_MEDICO = s.ID_MEDICO
  AND t.ES_ACTUAL = TRUE
  AND (
      t.ESPECIALIDAD IS DISTINCT FROM s.ESPECIALIDAD OR
      t.DEPARTAMENTO IS DISTINCT FROM s.DEPARTAMENTO
  );


-- ============================================================
-- PASO 3: INSERT — nueva version para registros cerrados en
--         paso 2 + medicos nuevos que aun no existen
-- ============================================================
INSERT INTO CONFORMED.DIM_MEDICO (
    ID_MEDICO, NOMBRE, APELLIDOS, NUMERO_COLEGIADO,
    TELEFONO, EMAIL, ESPECIALIDAD, DEPARTAMENTO,
    FECHA_INICIO, FECHA_FIN, ES_ACTUAL
)
SELECT
    m.ID_MEDICO,
    m.NOMBRE,
    m.APELLIDO1 || ' ' || m.APELLIDO2  AS APELLIDOS,
    m.NUMERO_COLEGIADO,
    m.TELEFONO,
    m.EMAIL,
    esp.NOMBRE_ESPECIALIDAD            AS ESPECIALIDAD,
    dep.NOMBRE_DEPARTAMENTO            AS DEPARTAMENTO,
    CURRENT_DATE,
    NULL,
    TRUE
FROM CLEANSED_MEDICARE.MEDICOS m
LEFT JOIN CLEANSED_MEDICARE.ESPECIALIDADES esp ON esp.ID_ESPECIALIDAD     = m.ID_ESPECIALIDAD
LEFT JOIN CLEANSED_MEDICARE.DEPARTAMENTOS  dep ON dep.CODIGO_DEPARTAMENTO = m.CODIGO_DEPARTAMENTO
WHERE NOT EXISTS (
    SELECT ID_MEDICO FROM CONFORMED.DIM_MEDICO
    WHERE ID_MEDICO = m.ID_MEDICO
      AND ES_ACTUAL = TRUE
);
