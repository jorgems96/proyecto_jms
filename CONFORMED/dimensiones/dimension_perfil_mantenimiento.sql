-- dimension_perfil_mantenimiento.sql
-- Dimension basura (junk dimension) de perfiles de mantenimiento
-- Contiene todas las combinaciones posibles de atributos categoricos
-- 4 x 4 x 3 x 2 x 2 = 192 combinaciones


--Esta dimensión es diferente a todas las anteriores: no tiene un ID_Perfil que venga de una tabla fuente, sino que es una dimensión basura (junk dimension). Agrupa combinaciones de flags y atributos categóricos de baja cardinalidad.

-- Esto significa que:

-- No hay tabla fuente en CLEANSED de la que leer — los valores son fijos y predefinidos
-- No hay lógica SCD — las combinaciones no cambian
-- Se pre-cargan todas las combinaciones posibles con un CROSS JOIN (4 × 4 × 3 × 2 × 2 = 192 combinaciones)
-- Es_Garantia y Requiere_Parada_Equipo los guardo como BOOLEAN en vez de VARCHAR 'Sí/No', que es más limpio


-- He quitado las tildes de Calibración, Inspección y Crítica 
-- para evitar problemas de encoding en Snowflake, 
-- igual que hicimos con dimension_fecha.sql. 
-- Un solo INSERT con CROSS JOIN carga las 192 combinaciones, 
-- y el WHERE NOT EXISTS evita duplicados si se ejecuta más de una vez.


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_PERFIL_MANTENIMIENTO (
    SK_PERFIL_MANTENIMIENTO NUMBER      NOT NULL AUTOINCREMENT PRIMARY KEY,
    TIPO_MANTENIMIENTO      VARCHAR(50) NOT NULL,
    PRIORIDAD               VARCHAR(20) NOT NULL,
    GRAVEDAD                VARCHAR(20) NOT NULL,
    ES_GARANTIA             BOOLEAN     NOT NULL,
    REQUIERE_PARADA_EQUIPO  BOOLEAN     NOT NULL
);


-- ============================================================
-- INSERT — cargar todas las combinaciones posibles
-- ============================================================
INSERT INTO CONFORMED.DIM_PERFIL_MANTENIMIENTO (
    TIPO_MANTENIMIENTO, PRIORIDAD, GRAVEDAD, ES_GARANTIA, REQUIERE_PARADA_EQUIPO
)
SELECT tipo, prioridad, gravedad, garantia, parada
FROM (VALUES ('Preventivo'), ('Correctivo'), ('Calibracion'), ('Inspeccion')) AS t(tipo)
CROSS JOIN (VALUES ('Baja'), ('Media'), ('Alta'), ('Critica'))               AS p(prioridad)
CROSS JOIN (VALUES ('Leve'), ('Moderada'), ('Grave'))                        AS g(gravedad)
CROSS JOIN (VALUES (TRUE), (FALSE))                                          AS ga(garantia)
CROSS JOIN (VALUES (TRUE), (FALSE))                                          AS pa(parada)
WHERE NOT EXISTS (
    SELECT SK_PERFIL_MANTENIMIENTO FROM CONFORMED.DIM_PERFIL_MANTENIMIENTO
    WHERE TIPO_MANTENIMIENTO     = tipo
      AND PRIORIDAD              = prioridad
      AND GRAVEDAD               = gravedad
      AND ES_GARANTIA            = garantia
      AND REQUIERE_PARADA_EQUIPO = parada
);


