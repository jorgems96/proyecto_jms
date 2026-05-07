-- dimension_equipo.sql
-- Dimension SCD1/SCD2 de equipos medicos
-- SCD1: Nombre_Equipo, Descripcion, Numero_Serie, Modelo, Fecha_Adquisicion, Fecha_Fin_Garantia, Clase_Riesgo
-- SCD2: Estado_Equipo, Departamento_Actual, Ubicacion_Actual
-- Fuente: CLEANSED_MEDICARE.EQUIPOS JOIN DEPARTAMENTOS JOIN UBICACIONES



CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_EQUIPO (
    SK_EQUIPO           NUMBER          NOT NULL AUTOINCREMENT PRIMARY KEY,
    ID_EQUIPO           NUMBER          NOT NULL,
    NOMBRE_EQUIPO       VARCHAR(200)    NOT NULL,
    DESCRIPCION         VARCHAR(500),
    NUMERO_SERIE        VARCHAR(100)    NOT NULL,
    MODELO              VARCHAR(200),
    FECHA_ADQUISICION   DATE,
    FECHA_FIN_GARANTIA  DATE,
    ESTADO_EQUIPO       VARCHAR(50)     NOT NULL,   -- SCD2
    CLASE_RIESGO        VARCHAR(10)     NOT NULL,
    DEPARTAMENTO_ACTUAL VARCHAR(200),               -- SCD2
    UBICACION_ACTUAL    VARCHAR(200),               -- SCD2
    FECHA_INICIO        DATE            NOT NULL,
    FECHA_FIN           DATE,
    ES_ACTUAL           BOOLEAN         NOT NULL    DEFAULT TRUE
);


-- ============================================================
-- PASO 1: SCD1 — actualizar en sitio sin guardar historial
-- ============================================================
UPDATE CONFORMED.DIM_EQUIPO t
SET
    NOMBRE_EQUIPO      = s.NOMBRE_EQUIPO,
    DESCRIPCION        = s.DESCRIPCION,
    NUMERO_SERIE       = s.NUMERO_SERIE,
    MODELO             = s.MODELO,
    FECHA_ADQUISICION  = s.FECHA_ADQUISICION,
    FECHA_FIN_GARANTIA = s.FECHA_FIN_GARANTIA,
    CLASE_RIESGO       = s.CLASE_RIESGO
FROM (
    SELECT
        ID_EQUIPO,
        NOMBRE_EQUIPO,
        DESCRIPCION,
        NUMERO_SERIE,
        MODELO,
        FECHA_ADQUISICION,
        FECHA_FIN_GARANTIA,
        CLASE_RIESGO
    FROM CLEANSED_MEDICARE.EQUIPOS
) s
WHERE t.ID_EQUIPO  = s.ID_EQUIPO
  AND t.ES_ACTUAL  = TRUE
  AND (
      t.NOMBRE_EQUIPO      IS DISTINCT FROM s.NOMBRE_EQUIPO      OR
      t.DESCRIPCION        IS DISTINCT FROM s.DESCRIPCION        OR
      t.NUMERO_SERIE       IS DISTINCT FROM s.NUMERO_SERIE       OR
      t.MODELO             IS DISTINCT FROM s.MODELO             OR
      t.FECHA_ADQUISICION  IS DISTINCT FROM s.FECHA_ADQUISICION  OR
      t.FECHA_FIN_GARANTIA IS DISTINCT FROM s.FECHA_FIN_GARANTIA OR
      t.CLASE_RIESGO       IS DISTINCT FROM s.CLASE_RIESGO
  );


-- ============================================================
-- PASO 2: SCD2 — cerrar version actual cuando cambia Estado,
--         Departamento o Ubicacion
-- ============================================================
UPDATE CONFORMED.DIM_EQUIPO t
SET
    FECHA_FIN = CURRENT_DATE - 1,
    ES_ACTUAL = FALSE
FROM (
    SELECT
        e.ID_EQUIPO,
        CASE e.ESTADO_CODIGO
            WHEN 1 THEN 'Activo'
            WHEN 2 THEN 'En Reparacion'
            WHEN 3 THEN 'Fuera de Servicio'
            WHEN 4 THEN 'Baja'
        END                                          AS ESTADO_EQUIPO,
        d.NOMBRE_DEPARTAMENTO                        AS DEPARTAMENTO_ACTUAL,
        u.EDIFICIO || ' - ' || u.SALA               AS UBICACION_ACTUAL
    FROM CLEANSED_MEDICARE.EQUIPOS e
    LEFT JOIN CLEANSED_MEDICARE.DEPARTAMENTOS d ON e.ID_DEPARTAMENTO = d.ID_DEPARTAMENTO
    LEFT JOIN CLEANSED_MEDICARE.UBICACIONES   u ON e.ID_UBICACION    = u.ID_UBICACION
) s
WHERE t.ID_EQUIPO  = s.ID_EQUIPO
  AND t.ES_ACTUAL  = TRUE
  AND (
      t.ESTADO_EQUIPO       IS DISTINCT FROM s.ESTADO_EQUIPO      OR
      t.DEPARTAMENTO_ACTUAL IS DISTINCT FROM s.DEPARTAMENTO_ACTUAL OR
      t.UBICACION_ACTUAL    IS DISTINCT FROM s.UBICACION_ACTUAL
  );


-- ============================================================
-- PASO 3: Insertar nueva version (registros cerrados en paso 2
--         + equipos nuevos que no existian aun)
-- ============================================================
INSERT INTO CONFORMED.DIM_EQUIPO (
    ID_EQUIPO, NOMBRE_EQUIPO, DESCRIPCION, NUMERO_SERIE, MODELO,
    FECHA_ADQUISICION, FECHA_FIN_GARANTIA, ESTADO_EQUIPO, CLASE_RIESGO,
    DEPARTAMENTO_ACTUAL, UBICACION_ACTUAL,
    FECHA_INICIO, FECHA_FIN, ES_ACTUAL
)
SELECT
    e.ID_EQUIPO,
    e.NOMBRE_EQUIPO,
    e.DESCRIPCION,
    e.NUMERO_SERIE,
    e.MODELO,
    e.FECHA_ADQUISICION,
    e.FECHA_FIN_GARANTIA,
    CASE e.ESTADO_CODIGO
        WHEN 1 THEN 'Activo'
        WHEN 2 THEN 'En Reparacion'
        WHEN 3 THEN 'Fuera de Servicio'
        WHEN 4 THEN 'Baja'
    END,
    e.CLASE_RIESGO,
    d.NOMBRE_DEPARTAMENTO,
    u.EDIFICIO || ' - ' || u.SALA,
    CURRENT_DATE,
    NULL,
    TRUE
FROM CLEANSED_MEDICARE.EQUIPOS e
LEFT JOIN CLEANSED_MEDICARE.DEPARTAMENTOS d ON e.ID_DEPARTAMENTO = d.ID_DEPARTAMENTO
LEFT JOIN CLEANSED_MEDICARE.UBICACIONES   u ON e.ID_UBICACION    = u.ID_UBICACION
WHERE NOT EXISTS (
    SELECT ID_EQUIPO FROM CONFORMED.DIM_EQUIPO
    WHERE ID_EQUIPO = e.ID_EQUIPO
      AND ES_ACTUAL = TRUE
);

