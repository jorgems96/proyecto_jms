-- dimension_tecnico.sql
-- Dimension SCD1/SCD2 de tecnicos de mantenimiento
-- SCD1: Nombre, Apellidos, Especialidad, Anios_Experiencia, Telefono, Email
-- SCD2: Departamento, Nivel_Certificacion
-- Fuente: CLEANSED_MEDICARE.TECNICOS
--
-- Nota de nomenclatura:
-- NOMBRE_TECNICO                     → NOMBRE (APELLIDOS pendiente de confirmar con profesor)
-- TELEFONO_MOVIL                     → TELEFONO
-- EMAIL_CORPORATIVO                  → EMAIL
-- DEPARTAMENTOS.NOMBRE_DEPARTAMENTO  → DEPARTAMENTO (JOIN por ID_DEPARTAMENTO)
-- NIVEL_CERTIFICACION (NUMBER):      → texto via CASE (mapeo por confirmar: 1=Junior, 2=Senior, 3=Especialista, 4=Jefe)


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_TECNICO (
    SK_TECNICO          NUMBER        NOT NULL AUTOINCREMENT PRIMARY KEY,
    ID_TECNICO          NUMBER        NOT NULL,
    NOMBRE              VARCHAR(200)  NOT NULL,
    APELLIDOS           VARCHAR(200),                -- pendiente confirmacion profesor
    ESPECIALIDAD        VARCHAR(200),
    ANIOS_EXPERIENCIA   NUMBER,
    TELEFONO            VARCHAR(50),
    EMAIL               VARCHAR(100),
    DEPARTAMENTO        VARCHAR(200),                -- SCD2
    NIVEL_CERTIFICACION VARCHAR(50),                 -- SCD2
    FECHA_INICIO        DATE          NOT NULL,
    FECHA_FIN           DATE,
    ES_ACTUAL           BOOLEAN       NOT NULL   DEFAULT TRUE
);


CALL CONFORMED.SP_MERGE_SCD1_SCD2(
    'CONFORMED.DIM_TECNICO',
    'SELECT
        tc.ID_TECNICO,
        tc.NOMBRE_TECNICO    AS NOMBRE,
        tc.ESPECIALIDAD,
        tc.ANIOS_EXPERIENCIA,
        tc.TELEFONO_MOVIL    AS TELEFONO,
        tc.EMAIL_CORPORATIVO AS EMAIL,
        dep.NOMBRE_DEPARTAMENTO AS DEPARTAMENTO,
        CASE tc.NIVEL_CERTIFICACION
            WHEN 1 THEN ''Junior''
            WHEN 2 THEN ''Senior''
            WHEN 3 THEN ''Especialista''
            WHEN 4 THEN ''Jefe''
        END                  AS NIVEL_CERTIFICACION
     FROM CLEANSED_MEDICARE.TECNICOS tc
     LEFT JOIN CLEANSED_MEDICARE.DEPARTAMENTOS dep ON dep.ID_DEPARTAMENTO = tc.ID_DEPARTAMENTO',
    'ID_TECNICO',
    'NOMBRE,ESPECIALIDAD,ANIOS_EXPERIENCIA,TELEFONO,EMAIL',
    'DEPARTAMENTO,NIVEL_CERTIFICACION'
);
