-- dimension_diagnostico.sql
-- Dimension SCD1 de diagnosticos CIE-10
-- Fuente: CLEANSED.DIAGNOSTICOS_CIE10
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


CALL CONFORMED.SP_MERGE_SCD1(
    'CONFORMED.DIM_DIAGNOSTICO',
    'SELECT
        ID_DIAGNOSTICO,
        CODIGO_CIE10,
        DESCRIPCION  AS DESCRIPCION_DIAGNOSTICO,
        CAPITULO     AS CATEGORIA,
        GRUPO        AS SUBCATEGORIA,
        ES_CRONICO
     FROM CLEANSED.DIAGNOSTICOS_CIE10',
    'ID_DIAGNOSTICO',
    'CODIGO_CIE10,DESCRIPCION_DIAGNOSTICO,CATEGORIA,SUBCATEGORIA,ES_CRONICO'
);
