-- dimension_ubicacion.sql
-- Dimension SCD1 de ubicaciones fisicas del hospital
-- Fuente: CLEANSED_MEDICARE.UBICACIONES


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_UBICACION (
    SK_UBICACION NUMBER       NOT NULL AUTOINCREMENT PRIMARY KEY,
    ID_UBICACION NUMBER       NOT NULL,
    EDIFICIO     VARCHAR(200) NOT NULL,
    PLANTA       NUMBER,
    ALA          VARCHAR(50),
    SALA         VARCHAR(100) NOT NULL,
    TIPO_SALA    VARCHAR(100),
    CAPACIDAD    NUMBER
);


-- ============================================================
-- PASO 1: SCD1 — actualizar en sitio sin guardar historial
-- ============================================================
UPDATE CONFORMED.DIM_UBICACION t
SET
    EDIFICIO  = s.EDIFICIO,
    PLANTA    = s.PLANTA,
    ALA       = s.ALA,
    SALA      = s.SALA,
    TIPO_SALA = s.TIPO_SALA,
    CAPACIDAD = s.CAPACIDAD
FROM (
    SELECT
        ID_UBICACION,
        EDIFICIO,
        PLANTA,
        ALA,
        SALA,
        TIPO_SALA,
        CAPACIDAD
    FROM CLEANSED_MEDICARE.UBICACIONES
) s
WHERE t.ID_UBICACION = s.ID_UBICACION
  AND (
      t.EDIFICIO  IS DISTINCT FROM s.EDIFICIO  OR
      t.PLANTA    IS DISTINCT FROM s.PLANTA    OR
      t.ALA       IS DISTINCT FROM s.ALA       OR
      t.SALA      IS DISTINCT FROM s.SALA      OR
      t.TIPO_SALA IS DISTINCT FROM s.TIPO_SALA OR
      t.CAPACIDAD IS DISTINCT FROM s.CAPACIDAD
  );


-- ============================================================
-- PASO 2: INSERT — ubicaciones nuevas que aun no existen
-- ============================================================
INSERT INTO CONFORMED.DIM_UBICACION (
    ID_UBICACION, EDIFICIO, PLANTA, ALA, SALA, TIPO_SALA, CAPACIDAD
)
SELECT
    ID_UBICACION,
    EDIFICIO,
    PLANTA,
    ALA,
    SALA,
    TIPO_SALA,
    CAPACIDAD
FROM CLEANSED_MEDICARE.UBICACIONES
WHERE NOT EXISTS (
    SELECT ID_UBICACION FROM CONFORMED.DIM_UBICACION
    WHERE ID_UBICACION = CLEANSED_MEDICARE.UBICACIONES.ID_UBICACION
);


--Son convenciones estándar en SQL — t de target (tabla destino) y s de source 
--(tabla fuente). Cualquier persona que trabaje con SQL los reconoce de inmediato, 
--así que sí son prácticos.

--La alternativa sería nombres más largos como destino y fuente, o usar el nombre de la 
--tabla directamente, pero eso último no funciona bien en UPDATE...FROM cuando
 --la misma tabla aparece en dos sitios.
--
--