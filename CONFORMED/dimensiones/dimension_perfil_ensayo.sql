-- dimension_perfil_ensayo.sql
-- Dimension basura (junk dimension) de perfiles de ensayo clinico
-- Contiene todas las combinaciones posibles de atributos categoricos
-- 4 x 3 x 2 x 3 x 5 = 360 combinaciones

--He quitado las tildes de Subcutánea y Tópica para evitar problemas de encoding en Snowflake. 
--Un solo INSERT con CROSS JOIN carga las 360 combinaciones, 
--y el WHERE NOT EXISTS evita duplicados si se ejecuta más de una vez.


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_PERFIL_ENSAYO (
    SK_PERFIL_ENSAYO    NUMBER      NOT NULL AUTOINCREMENT PRIMARY KEY,
    FASE_ENSAYO         VARCHAR(20) NOT NULL,
    TIPO_CIEGO          VARCHAR(30) NOT NULL,
    TIPO_ALEATORIZACION VARCHAR(30) NOT NULL,
    GRUPO_TRATAMIENTO   VARCHAR(30) NOT NULL,
    VIA_ADMINISTRACION  VARCHAR(30) NOT NULL
);


-- ============================================================
-- INSERT — cargar todas las combinaciones posibles
-- ============================================================
INSERT INTO CONFORMED.DIM_PERFIL_ENSAYO (
    FASE_ENSAYO, TIPO_CIEGO, TIPO_ALEATORIZACION, GRUPO_TRATAMIENTO, VIA_ADMINISTRACION
)
SELECT fase, ciego, aleatorizacion, grupo, via
FROM (VALUES ('Fase I'), ('Fase II'), ('Fase III'), ('Fase IV'))                   AS f(fase)
CROSS JOIN (VALUES ('Abierto'), ('Simple Ciego'), ('Doble Ciego'))                 AS c(ciego)
CROSS JOIN (VALUES ('Aleatorizado'), ('No Aleatorizado'))                          AS a(aleatorizacion)
CROSS JOIN (VALUES ('Experimental'), ('Control'), ('Placebo'))                     AS g(grupo)
CROSS JOIN (VALUES ('Oral'), ('Intravenosa'), ('Subcutanea'), ('Topica'), ('Inhalatoria')) AS v(via)
WHERE NOT EXISTS (
    SELECT SK_PERFIL_ENSAYO FROM CONFORMED.DIM_PERFIL_ENSAYO
    WHERE FASE_ENSAYO         = fase
      AND TIPO_CIEGO          = ciego
      AND TIPO_ALEATORIZACION = aleatorizacion
      AND GRUPO_TRATAMIENTO   = grupo
      AND VIA_ADMINISTRACION  = via
);
