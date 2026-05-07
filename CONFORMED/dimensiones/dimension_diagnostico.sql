-- dimension_diagnostico.sql
-- Dimension SCD1 de diagnosticos CIE-10
-- Fuente: CLEANSED_MEDICARE.DIAGNOSTICOS_CIE10
--
-- Nota de nomenclatura: los nombres de columna de la dimension difieren de la fuente
-- en tres campos. Se mantienen los nombres del spec (DESCRIPCION_DIAGNOSTICO,
-- CATEGORIA, SUBCATEGORIA) en lugar de los de la fuente (DESCRIPCION, CAPITULO, GRUPO)
-- porque la capa CONFORMED debe ser autoexplicativa para herramientas BI sin
-- requerir conocer la nomenclatura interna de la fuente.
-- El mapeo se resuelve con alias en el SELECT de cada operacion.


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_DIAGNOSTICO (
    SK_DIAGNOSTICO          NUMBER        NOT NULL AUTOINCREMENT PRIMARY KEY,
    ID_DIAGNOSTICO          NUMBER        NOT NULL,
    CODIGO_CIE10            VARCHAR(10)   NOT NULL,
    DESCRIPCION_DIAGNOSTICO VARCHAR(500)  NOT NULL,
    CATEGORIA               VARCHAR(200),
    SUBCATEGORIA            VARCHAR(200),
    ES_CRONICO              BOOLEAN
);


-- ============================================================
-- PASO 1: SCD1 — actualizar en sitio sin guardar historial
-- ============================================================
UPDATE CONFORMED.DIM_DIAGNOSTICO t
SET
    CODIGO_CIE10            = s.CODIGO_CIE10,
    DESCRIPCION_DIAGNOSTICO = s.DESCRIPCION_DIAGNOSTICO,
    CATEGORIA               = s.CATEGORIA,
    SUBCATEGORIA            = s.SUBCATEGORIA,
    ES_CRONICO              = s.ES_CRONICO
FROM (
    SELECT
        ID_DIAGNOSTICO,
        CODIGO_CIE10,
        DESCRIPCION  AS DESCRIPCION_DIAGNOSTICO,
        CAPITULO     AS CATEGORIA,
        GRUPO        AS SUBCATEGORIA,
        ES_CRONICO
    FROM CLEANSED_MEDICARE.DIAGNOSTICOS_CIE10
) s
WHERE t.ID_DIAGNOSTICO = s.ID_DIAGNOSTICO
  AND (
      t.CODIGO_CIE10            IS DISTINCT FROM s.CODIGO_CIE10            OR
      t.DESCRIPCION_DIAGNOSTICO IS DISTINCT FROM s.DESCRIPCION_DIAGNOSTICO OR
      t.CATEGORIA               IS DISTINCT FROM s.CATEGORIA               OR
      t.SUBCATEGORIA            IS DISTINCT FROM s.SUBCATEGORIA            OR
      t.ES_CRONICO              IS DISTINCT FROM s.ES_CRONICO
  );


-- ============================================================
-- PASO 2: INSERT — diagnosticos nuevos que aun no existen
-- ============================================================
INSERT INTO CONFORMED.DIM_DIAGNOSTICO (
    ID_DIAGNOSTICO, CODIGO_CIE10, DESCRIPCION_DIAGNOSTICO,
    CATEGORIA, SUBCATEGORIA, ES_CRONICO
)
SELECT
    ID_DIAGNOSTICO,
    CODIGO_CIE10,
    DESCRIPCION  AS DESCRIPCION_DIAGNOSTICO,
    CAPITULO     AS CATEGORIA,
    GRUPO        AS SUBCATEGORIA,
    ES_CRONICO
FROM CLEANSED_MEDICARE.DIAGNOSTICOS_CIE10
WHERE NOT EXISTS (
    SELECT ID_DIAGNOSTICO FROM CONFORMED.DIM_DIAGNOSTICO
    WHERE ID_DIAGNOSTICO = CLEANSED_MEDICARE.DIAGNOSTICOS_CIE10.ID_DIAGNOSTICO
);
