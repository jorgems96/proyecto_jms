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


-- ============================================================
-- PASO 1: SCD1 — actualizar en sitio sin guardar historial
-- ============================================================
UPDATE CONFORMED.DIM_TECNICO t
SET
    NOMBRE            = s.NOMBRE,
    ESPECIALIDAD      = s.ESPECIALIDAD,
    ANIOS_EXPERIENCIA = s.ANIOS_EXPERIENCIA,
    TELEFONO          = s.TELEFONO,
    EMAIL             = s.EMAIL
FROM (
    SELECT
        ID_TECNICO,
        NOMBRE_TECNICO      AS NOMBRE,
        ESPECIALIDAD,
        ANIOS_EXPERIENCIA,
        TELEFONO_MOVIL      AS TELEFONO,
        EMAIL_CORPORATIVO   AS EMAIL
    FROM CLEANSED_MEDICARE.TECNICOS
) s
WHERE t.ID_TECNICO = s.ID_TECNICO
  AND t.ES_ACTUAL  = TRUE
  AND (
      t.NOMBRE            IS DISTINCT FROM s.NOMBRE            OR
      t.ESPECIALIDAD      IS DISTINCT FROM s.ESPECIALIDAD      OR
      t.ANIOS_EXPERIENCIA IS DISTINCT FROM s.ANIOS_EXPERIENCIA OR
      t.TELEFONO          IS DISTINCT FROM s.TELEFONO          OR
      t.EMAIL             IS DISTINCT FROM s.EMAIL
  );


-- ============================================================
-- PASO 2: SCD2 — cerrar version actual cuando cambia
--         Departamento o Nivel_Certificacion
-- ============================================================
UPDATE CONFORMED.DIM_TECNICO t
SET
    FECHA_FIN = CURRENT_DATE - 1,
    ES_ACTUAL = FALSE
FROM (
    SELECT
        tc.ID_TECNICO,
        dep.NOMBRE_DEPARTAMENTO                    AS DEPARTAMENTO,
        CASE tc.NIVEL_CERTIFICACION
            WHEN 1 THEN 'Junior'
            WHEN 2 THEN 'Senior'
            WHEN 3 THEN 'Especialista'
            WHEN 4 THEN 'Jefe'
        END                                        AS NIVEL_CERTIFICACION
    FROM CLEANSED_MEDICARE.TECNICOS tc
    LEFT JOIN CLEANSED_MEDICARE.DEPARTAMENTOS dep ON dep.ID_DEPARTAMENTO = tc.ID_DEPARTAMENTO
) s
WHERE t.ID_TECNICO = s.ID_TECNICO
  AND t.ES_ACTUAL  = TRUE
  AND (
      t.DEPARTAMENTO        IS DISTINCT FROM s.DEPARTAMENTO        OR
      t.NIVEL_CERTIFICACION IS DISTINCT FROM s.NIVEL_CERTIFICACION
  );


-- ============================================================
-- PASO 3: INSERT — nueva version para registros cerrados en
--         paso 2 + tecnicos nuevos que aun no existen
-- ============================================================
INSERT INTO CONFORMED.DIM_TECNICO (
    ID_TECNICO, NOMBRE, ESPECIALIDAD, ANIOS_EXPERIENCIA,
    TELEFONO, EMAIL, DEPARTAMENTO, NIVEL_CERTIFICACION,
    FECHA_INICIO, FECHA_FIN, ES_ACTUAL
)
SELECT
    tc.ID_TECNICO,
    tc.NOMBRE_TECNICO                              AS NOMBRE,
    tc.ESPECIALIDAD,
    tc.ANIOS_EXPERIENCIA,
    tc.TELEFONO_MOVIL                              AS TELEFONO,
    tc.EMAIL_CORPORATIVO                           AS EMAIL,
    dep.NOMBRE_DEPARTAMENTO                        AS DEPARTAMENTO,
    CASE tc.NIVEL_CERTIFICACION
        WHEN 1 THEN 'Junior'
        WHEN 2 THEN 'Senior'
        WHEN 3 THEN 'Especialista'
        WHEN 4 THEN 'Jefe'
    END                                            AS NIVEL_CERTIFICACION,
    CURRENT_DATE,
    NULL,
    TRUE
FROM CLEANSED_MEDICARE.TECNICOS tc
LEFT JOIN CLEANSED_MEDICARE.DEPARTAMENTOS dep ON dep.ID_DEPARTAMENTO = tc.ID_DEPARTAMENTO
WHERE NOT EXISTS (
    SELECT ID_TECNICO FROM CONFORMED.DIM_TECNICO
    WHERE ID_TECNICO = tc.ID_TECNICO
      AND ES_ACTUAL  = TRUE
);
