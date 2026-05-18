-- view_dimensiones.sql
-- Definicion de referencia de las vistas de dimensiones en OPTIMIZED.
-- Este fichero es solo documentacion/lectura.
-- Las vistas se crean o actualizan llamando a: CALL OPTIMIZED.SP_DEPLOY_OPTIMIZED()  (FASE 5)

--ESTE FICHERO NO EJECUTA NI CREA NADA, ES SIMPLE DOCUMENTACION DE APOYO 
--PARA ENTENDER LAS REFERENCIAS DE LOS NOMBRES DE CAMPOS EN LAS DIMENSIONESç
--en este caso, el mismo codigo está en el fichero del SP, pero sin los comentarios explicativos, 
--para que se ejecute sin problemas.

-- -------------------------------------------------------
-- DIM_FECHA
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_FECHA AS
SELECT * FROM CONFORMED.DIM_FECHA;

-- -------------------------------------------------------
-- DIM_DEPARTAMENTO
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_DEPARTAMENTO AS
SELECT * FROM CONFORMED.DIM_DEPARTAMENTO;

-- -------------------------------------------------------
-- DIM_UBICACION
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_UBICACION AS
SELECT * FROM CONFORMED.DIM_UBICACION;

-- -------------------------------------------------------
-- DIM_FABRICANTE
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_FABRICANTE AS
SELECT * FROM CONFORMED.DIM_FABRICANTE;

-- -------------------------------------------------------
-- DIM_ENSAYO
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_ENSAYO AS
SELECT * FROM CONFORMED.DIM_ENSAYO;

-- -------------------------------------------------------
-- DIM_DIAGNOSTICO
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_DIAGNOSTICO AS
SELECT * FROM CONFORMED.DIM_DIAGNOSTICO;

-- -------------------------------------------------------
-- DIM_PERFIL_MANTENIMIENTO
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_PERFIL_MANTENIMIENTO AS
SELECT * FROM CONFORMED.DIM_PERFIL_MANTENIMIENTO;

-- -------------------------------------------------------
-- DIM_PERFIL_ENSAYO
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_PERFIL_ENSAYO AS
SELECT * FROM CONFORMED.DIM_PERFIL_ENSAYO;

-- -------------------------------------------------------
-- DIM_MEDICO (SCD2: solo version vigente)
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_MEDICO AS
SELECT * FROM CONFORMED.DIM_MEDICO WHERE ES_ACTUAL = TRUE;

-- -------------------------------------------------------
-- DIM_TECNICO (SCD2: solo version vigente)
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_TECNICO AS
SELECT * FROM CONFORMED.DIM_TECNICO WHERE ES_ACTUAL = TRUE;

-- -------------------------------------------------------
-- DIM_PACIENTE (SCD2: solo version vigente)
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_PACIENTE AS
SELECT * FROM CONFORMED.DIM_PACIENTE WHERE ES_ACTUAL = TRUE;

-- -------------------------------------------------------
-- DIM_EQUIPO (SCD2: solo version vigente)
-- -------------------------------------------------------
CREATE OR REPLACE VIEW OPTIMIZED.DIM_EQUIPO AS
SELECT * FROM CONFORMED.DIM_EQUIPO WHERE ES_ACTUAL = TRUE;
