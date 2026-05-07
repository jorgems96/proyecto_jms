-- dimension_paciente.sql
-- Dimension SCD1/SCD2 de pacientes
-- SCD1: Nombre, Apellidos, Fecha_Nacimiento, Genero, Telefono, Email, Grupo_Sanguineo
-- SCD2: Direccion, Ciudad, Codigo_Postal, Seguro_Medico, Tipo_Seguro
-- Fuente: CLEANSED_MEDICARE.PACIENTES
--
-- Nota de nomenclatura: varios campos difieren entre el spec y la fuente.
-- Se mantienen los nombres del spec en la dimension y se resuelve con alias en el SELECT:
-- APELLIDO1 || ' ' || APELLIDO2 → APELLIDOS
-- SEXO                          → GENERO
-- COMPANIA_SEGURO               → SEGURO_MEDICO
-- TIPO_COBERTURA                → TIPO_SEGURO
-- TELEFONO_MOVIL                → TELEFONO


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_PACIENTE (
    SK_PACIENTE      NUMBER        NOT NULL AUTOINCREMENT PRIMARY KEY,
    ID_PACIENTE      NUMBER        NOT NULL,
    NOMBRE           VARCHAR(100)  NOT NULL,
    APELLIDOS        VARCHAR(200)  NOT NULL,
    FECHA_NACIMIENTO DATE,
    GENERO           VARCHAR(20),
    TELEFONO         VARCHAR(50),
    EMAIL            VARCHAR(100),
    GRUPO_SANGUINEO  VARCHAR(5),
    DIRECCION        VARCHAR(300),
    CIUDAD           VARCHAR(100),
    CODIGO_POSTAL    VARCHAR(10),
    SEGURO_MEDICO    VARCHAR(200),
    TIPO_SEGURO      VARCHAR(50),
    FECHA_INICIO     DATE          NOT NULL,
    FECHA_FIN        DATE,
    ES_ACTUAL        BOOLEAN       NOT NULL   DEFAULT TRUE
);


-- ============================================================
-- PASO 1: SCD1 — actualizar en sitio sin guardar historial
-- ============================================================
UPDATE CONFORMED.DIM_PACIENTE t
SET
    NOMBRE           = s.NOMBRE,
    APELLIDOS        = s.APELLIDOS,
    FECHA_NACIMIENTO = s.FECHA_NACIMIENTO,
    GENERO           = s.GENERO,
    TELEFONO         = s.TELEFONO,
    EMAIL            = s.EMAIL,
    GRUPO_SANGUINEO  = s.GRUPO_SANGUINEO
FROM (
    SELECT
        ID_PACIENTE,
        NOMBRE,
        APELLIDO1 || ' ' || APELLIDO2  AS APELLIDOS,
        FECHA_NACIMIENTO,
        SEXO                           AS GENERO,
        TELEFONO_MOVIL                 AS TELEFONO,
        EMAIL,
        GRUPO_SANGUINEO
    FROM CLEANSED_MEDICARE.PACIENTES
) s
WHERE t.ID_PACIENTE = s.ID_PACIENTE
  AND t.ES_ACTUAL   = TRUE
  AND (
      t.NOMBRE           IS DISTINCT FROM s.NOMBRE           OR
      t.APELLIDOS        IS DISTINCT FROM s.APELLIDOS        OR
      t.FECHA_NACIMIENTO IS DISTINCT FROM s.FECHA_NACIMIENTO OR
      t.GENERO           IS DISTINCT FROM s.GENERO           OR
      t.TELEFONO         IS DISTINCT FROM s.TELEFONO         OR
      t.EMAIL            IS DISTINCT FROM s.EMAIL            OR
      t.GRUPO_SANGUINEO  IS DISTINCT FROM s.GRUPO_SANGUINEO
  );


-- ============================================================
-- PASO 2: SCD2 — cerrar version actual cuando cambia
--         Direccion, Ciudad, Codigo_Postal, Seguro_Medico o Tipo_Seguro
-- ============================================================
UPDATE CONFORMED.DIM_PACIENTE t
SET
    FECHA_FIN = CURRENT_DATE - 1,
    ES_ACTUAL = FALSE
FROM (
    SELECT
        ID_PACIENTE,
        DIRECCION,
        CIUDAD,
        CODIGO_POSTAL,
        COMPANIA_SEGURO  AS SEGURO_MEDICO,
        TIPO_COBERTURA   AS TIPO_SEGURO
    FROM CLEANSED_MEDICARE.PACIENTES
) s
WHERE t.ID_PACIENTE = s.ID_PACIENTE
  AND t.ES_ACTUAL   = TRUE
  AND (
      t.DIRECCION     IS DISTINCT FROM s.DIRECCION     OR
      t.CIUDAD        IS DISTINCT FROM s.CIUDAD        OR
      t.CODIGO_POSTAL IS DISTINCT FROM s.CODIGO_POSTAL OR
      t.SEGURO_MEDICO IS DISTINCT FROM s.SEGURO_MEDICO OR
      t.TIPO_SEGURO   IS DISTINCT FROM s.TIPO_SEGURO
  );


-- ============================================================
-- PASO 3: INSERT — nueva version para registros cerrados en
--         paso 2 + pacientes nuevos que aun no existen
-- ============================================================
INSERT INTO CONFORMED.DIM_PACIENTE (
    ID_PACIENTE, NOMBRE, APELLIDOS, FECHA_NACIMIENTO, GENERO,
    TELEFONO, EMAIL, GRUPO_SANGUINEO,
    DIRECCION, CIUDAD, CODIGO_POSTAL, SEGURO_MEDICO, TIPO_SEGURO,
    FECHA_INICIO, FECHA_FIN, ES_ACTUAL
)
SELECT
    ID_PACIENTE,
    NOMBRE,
    APELLIDO1 || ' ' || APELLIDO2  AS APELLIDOS,
    FECHA_NACIMIENTO,
    SEXO                           AS GENERO,
    TELEFONO_MOVIL                 AS TELEFONO,
    EMAIL,
    GRUPO_SANGUINEO,
    DIRECCION,
    CIUDAD,
    CODIGO_POSTAL,
    COMPANIA_SEGURO                AS SEGURO_MEDICO,
    TIPO_COBERTURA                 AS TIPO_SEGURO,
    CURRENT_DATE,
    NULL,
    TRUE
FROM CLEANSED_MEDICARE.PACIENTES
WHERE NOT EXISTS (
    SELECT ID_PACIENTE FROM CONFORMED.DIM_PACIENTE
    WHERE ID_PACIENTE = CLEANSED_MEDICARE.PACIENTES.ID_PACIENTE
      AND ES_ACTUAL   = TRUE
);
