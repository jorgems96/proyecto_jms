-- fact_ensayos_clinicos.sql
-- Tabla de hechos de ensayos clinicos con granularidad diaria
-- Granularidad: una fila por visita (VISITAS_ENSAYO ya tiene granularidad diaria,
--              no es necesario expandir rangos de fechas)
-- Fuentes principales:
--   CLEANSED.VISITAS_ENSAYO       (medidas y fecha de visita)
--   CLEANSED.PARTICIPACION_ENSAYOS (claves de participacion y atributos junk)
--   CLEANSED.ENSAYOS_CLINICOS     (CODIGO_DEPARTAMENTO para resolver SK_DEPARTAMENTO)
--
-- Nota de nomenclatura:
--   ID_VISITA              → dimension degenerada (identificador unico de la visita)
--   FECHA_VISITA           → SK_FECHA
--   ID_MEDICO_ASIGNADO     → SK_MEDICO
--   FASE                   → FASE_ENSAYO  (atributo junk dimension)
--   GRUPO_ASIGNADO         → GRUPO_TRATAMIENTO (atributo junk dimension)
--   NUMERO_VISITAS_DIA     → eliminado (no existe en la fuente)
--   SK_DEPARTAMENTO        → resuelto via ENSAYOS_CLINICOS.CODIGO_DEPARTAMENTO → DEPARTAMENTOS


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.FACT_ENSAYOS_CLINICOS (
    SK_ENSAYO_CLINICO              NUMBER    NOT NULL AUTOINCREMENT PRIMARY KEY,
    -- Claves foraneas
    SK_FECHA                       NUMBER    NOT NULL,  -- FK → DIM_FECHA (dia de la visita)
    SK_FECHA_INICIO                NUMBER    NOT NULL,  -- FK → DIM_FECHA (inicio participacion)
    SK_FECHA_FIN                   NUMBER    NOT NULL,  -- FK → DIM_FECHA (fin participacion)
    SK_ENSAYO                      NUMBER    NOT NULL,  -- FK → DIM_ENSAYO
    SK_PACIENTE                    NUMBER    NOT NULL,  -- FK → DIM_PACIENTE
    SK_MEDICO                      NUMBER    NOT NULL,  -- FK → DIM_MEDICO
    SK_DIAGNOSTICO                 NUMBER    NOT NULL,  -- FK → DIM_DIAGNOSTICO
    SK_DEPARTAMENTO                NUMBER    NOT NULL,  -- FK → DIM_DEPARTAMENTO
    SK_PERFIL_ENSAYO               NUMBER    NOT NULL,  -- FK → DIM_PERFIL_ENSAYO
    -- Dimension degenerada
    ID_VISITA                      NUMBER    NOT NULL,
    -- Medidas aditivas
    DOSIS_ADMINISTRADA             NUMBER(10,4),
    UNIDAD_DOSIS                   VARCHAR(10),
    NUMERO_EFECTOS_ADVERSOS        NUMBER,
    -- Medidas semi-aditivas (no sumar entre visitas, usar AVG o last-value)
    RESULTADO_MEDICION_PRINCIPAL   NUMBER(8,4),
    RESULTADO_MEDICION_SECUNDARIA  NUMBER(8,4),
    NIVEL_EFICACIA                 NUMBER(5,4)
);


-- Restricciones de clave foranea (informativas en Snowflake, utiles para BI tools)
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS  -- aqui SK_FECHA es la fecha de la visita, no el inicio o fin de participacion
    ADD CONSTRAINT FK_ENS_FECHA        FOREIGN KEY (SK_FECHA)         REFERENCES CONFORMED.DIM_FECHA(SK_FECHA); -- aqui lo que hago es asegurar que la fecha de la visita exista 
    --en la dimension de fechas, aunque no sea la fecha de inicio o fin de participacion. 
    --Esto es importante para mantener la integridad referencial 
    -- y facilitar el análisis temporal de las visitas en los ensayos clínicos.
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS -- aqui SK_FECHA_INICIO es la fecha de inicio de participacion del paciente en el ensayo
    ADD CONSTRAINT FK_ENS_FECHA_INI    FOREIGN KEY (SK_FECHA_INICIO)  REFERENCES CONFORMED.DIM_FECHA(SK_FECHA); -- aqui lo que hago es asegurar que la fecha de inicio de participacion del paciente en el ensayo exista en la dimension de fechas, 
    --aunque no sea la fecha de la visita o la fecha de fin de participacion. Esto es importante
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS -- aqui SK_FECHA_FIN es la fecha de fin de participacion del paciente en el ensayo
    ADD CONSTRAINT FK_ENS_FECHA_FIN    FOREIGN KEY (SK_FECHA_FIN)     REFERENCES CONFORMED.DIM_FECHA(SK_FECHA);
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS
    ADD CONSTRAINT FK_ENS_ENSAYO       FOREIGN KEY (SK_ENSAYO)        REFERENCES CONFORMED.DIM_ENSAYO(SK_ENSAYO);
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS
    ADD CONSTRAINT FK_ENS_PACIENTE     FOREIGN KEY (SK_PACIENTE)      REFERENCES CONFORMED.DIM_PACIENTE(SK_PACIENTE);
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS
    ADD CONSTRAINT FK_ENS_MEDICO       FOREIGN KEY (SK_MEDICO)        REFERENCES CONFORMED.DIM_MEDICO(SK_MEDICO);
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS
    ADD CONSTRAINT FK_ENS_DIAG         FOREIGN KEY (SK_DIAGNOSTICO)   REFERENCES CONFORMED.DIM_DIAGNOSTICO(SK_DIAGNOSTICO);
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS
    ADD CONSTRAINT FK_ENS_DEPTO        FOREIGN KEY (SK_DEPARTAMENTO)  REFERENCES CONFORMED.DIM_DEPARTAMENTO(SK_DEPARTAMENTO);
ALTER TABLE CONFORMED.FACT_ENSAYOS_CLINICOS
    ADD CONSTRAINT FK_ENS_PERFIL       FOREIGN KEY (SK_PERFIL_ENSAYO) REFERENCES CONFORMED.DIM_PERFIL_ENSAYO(SK_PERFIL_ENSAYO);


-- ============================================================
-- INSERT — cargar visitas de ensayos nuevas
-- ============================================================
INSERT INTO CONFORMED.FACT_ENSAYOS_CLINICOS (
    SK_FECHA, SK_FECHA_INICIO, SK_FECHA_FIN,
    SK_ENSAYO, SK_PACIENTE, SK_MEDICO, SK_DIAGNOSTICO,
    SK_DEPARTAMENTO, SK_PERFIL_ENSAYO, ID_VISITA,
    DOSIS_ADMINISTRADA, UNIDAD_DOSIS, NUMERO_EFECTOS_ADVERSOS,
    RESULTADO_MEDICION_PRINCIPAL, RESULTADO_MEDICION_SECUNDARIA, NIVEL_EFICACIA
)
SELECT
    TO_NUMBER(TO_CHAR(v.FECHA_VISITA, 'YYYYMMDD'))                        AS SK_FECHA,
    TO_NUMBER(TO_CHAR(p.FECHA_INICIO_PARTICIPACION, 'YYYYMMDD'))          AS SK_FECHA_INICIO,
    TO_NUMBER(TO_CHAR(p.FECHA_FIN_PARTICIPACION,    'YYYYMMDD'))          AS SK_FECHA_FIN,
    en.SK_ENSAYO,
    pa.SK_PACIENTE,
    me.SK_MEDICO,
    di.SK_DIAGNOSTICO,
    dp.SK_DEPARTAMENTO,
    pe.SK_PERFIL_ENSAYO,
    v.ID_VISITA,
    v.DOSIS_ADMINISTRADA,
    v.UNIDAD_DOSIS,
    v.NUMERO_EFECTOS_ADVERSOS,
    v.RESULTADO_MEDICION_PRINCIPAL,
    v.RESULTADO_MEDICION_SECUNDARIA,
    v.NIVEL_EFICACIA
FROM CLEANSED.VISITAS_ENSAYO v
JOIN CLEANSED.PARTICIPACION_ENSAYOS  p   ON p.ID_PARTICIPACION    = v.ID_PARTICIPACION
JOIN CLEANSED.ENSAYOS_CLINICOS       ec  ON ec.ID_ENSAYO          = p.ID_ENSAYO
-- Resolver CODIGO_DEPARTAMENTO del ensayo a ID para el JOIN a la dimension
JOIN CLEANSED.DEPARTAMENTOS          dep_src ON dep_src.CODIGO_DEPARTAMENTO = ec.CODIGO_DEPARTAMENTO
-- Dimensiones conformed
JOIN CONFORMED.DIM_ENSAYO           en ON en.ID_ENSAYO       = p.ID_ENSAYO
JOIN CONFORMED.DIM_PACIENTE         pa ON pa.ID_PACIENTE      = p.ID_PACIENTE      AND pa.ES_ACTUAL = TRUE
JOIN CONFORMED.DIM_MEDICO           me ON me.ID_MEDICO        = p.ID_MEDICO_ASIGNADO AND me.ES_ACTUAL = TRUE
JOIN CONFORMED.DIM_DIAGNOSTICO      di ON di.ID_DIAGNOSTICO   = p.ID_DIAGNOSTICO
JOIN CONFORMED.DIM_DEPARTAMENTO     dp ON dp.ID_DEPARTAMENTO  = dep_src.ID_DEPARTAMENTO
JOIN CONFORMED.DIM_PERFIL_ENSAYO    pe ON pe.FASE_ENSAYO         = p.FASE
                                      AND pe.TIPO_CIEGO           = p.TIPO_CIEGO
                                      AND pe.TIPO_ALEATORIZACION  = p.TIPO_ALEATORIZACION
                                      AND pe.GRUPO_TRATAMIENTO    = p.GRUPO_ASIGNADO
                                      AND pe.VIA_ADMINISTRACION   = p.VIA_ADMINISTRACION
WHERE NOT EXISTS (
    SELECT ID_VISITA FROM CONFORMED.FACT_ENSAYOS_CLINICOS
    WHERE ID_VISITA = v.ID_VISITA
);
