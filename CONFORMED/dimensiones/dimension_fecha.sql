-- dimension_fecha.sql
-- Dimensión de fecha conformed: 2015-01-01 → 2030-12-31 (5.844 días)
-- Sin festivos de momento (ES_FESTIVO = FALSE para todos)

CREATE OR REPLACE TABLE CONFORMED.DIM_FECHA AS
WITH SERIE AS (
    -- SEQ4() arranca en 0, por lo que ROWCOUNT = 5844 genera del día 0 al 5843
    SELECT DATEADD(DAY, SEQ4(), '2015-01-01'::DATE) AS FECHA
    FROM TABLE(GENERATOR(ROWCOUNT => 5844))
)
SELECT
    TO_NUMBER(TO_CHAR(FECHA, 'YYYYMMDD'))                   AS SK_FECHA,       -- PK numerica formato YYYYMMDD
    FECHA                                                   AS FECHA,
    YEAR(FECHA)                                             AS ANIO,
    CASE WHEN MONTH(FECHA) <= 6 THEN 1 ELSE 2 END          AS SEMESTRE,
    QUARTER(FECHA)                                          AS TRIMESTRE,
    MONTH(FECHA)                                            AS MES,
    CASE MONTH(FECHA)
        WHEN 1  THEN 'Enero'        WHEN 2  THEN 'Febrero'
        WHEN 3  THEN 'Marzo'        WHEN 4  THEN 'Abril'
        WHEN 5  THEN 'Mayo'         WHEN 6  THEN 'Junio'
        WHEN 7  THEN 'Julio'        WHEN 8  THEN 'Agosto'
        WHEN 9  THEN 'Septiembre'   WHEN 10 THEN 'Octubre'
        WHEN 11 THEN 'Noviembre'    WHEN 12 THEN 'Diciembre'
    END                                                     AS NOMBRE_MES,
    WEEKISO(FECHA)                                          AS SEMANA_ANIO,    -- semana ISO garantizada
    DAY(FECHA)                                              AS DIA,
    DAYOFWEEKISO(FECHA)                                     AS DIA_SEMANA,     -- 1 = Lunes ... 7 = Domingo (ISO)
    CASE DAYOFWEEKISO(FECHA)
        WHEN 1 THEN 'Lunes'         WHEN 2 THEN 'Martes'
        WHEN 3 THEN 'Miercoles'     WHEN 4 THEN 'Jueves'
        WHEN 5 THEN 'Viernes'       WHEN 6 THEN 'Sabado'
        WHEN 7 THEN 'Domingo'
    END                                                     AS NOMBRE_DIA,
    DAYOFWEEKISO(FECHA) IN (6, 7)                          AS ES_FIN_SEMANA,
    FALSE                                                   AS ES_FESTIVO
FROM SERIE;

ALTER TABLE CONFORMED.DIM_FECHA
    ADD CONSTRAINT PK_DIM_FECHA PRIMARY KEY (SK_FECHA);

