-- dimension_paciente.sql
-- Dimension SCD1/SCD2 de pacientes
-- SCD1: Nombre, Apellidos, Fecha_Nacimiento, Genero, Telefono, Email, Grupo_Sanguineo
-- SCD2: Direccion, Ciudad, Codigo_Postal, Seguro_Medico, Tipo_Seguro
-- Fuente: CLEANSED.PACIENTES
--
-- Nota de nomenclatura: varios campos difieren entre el spec y la fuente.
-- Se mantienen los nombres del spec en la dimension y se resuelve con alias en el SELECT:
-- APELLIDO1 || ' ' || APELLIDO2 → APELLIDOS
-- SEXO                          → GENERO
-- COMPANIA_SEGURO               → SEGURO_MEDICO
-- TIPO_COBERTURA                → TIPO_SEGURO
-- TELEFONO_MOVIL                → TELEFONO


CREATE SCHEMA IF NOT EXISTS CONFORMED;

CREATE TABLE IF NOT EXISTS CONFORMED.DIM_PACIENTE (
    SK_PACIENTE      NUMBER        NOT NULL AUTOINCREMENT PRIMARY KEY,
    ID_PACIENTE      NUMBER        NOT NULL,
    NOMBRE           VARCHAR(100)  NOT NULL,
    APELLIDOS        VARCHAR(200)  NOT NULL,
    FECHA_NACIMIENTO DATE,
    GENERO           VARCHAR(20),
    TELEFONO         VARCHAR(50),
    EMAIL            VARCHAR(100),
    GRUPO_SANGUINEO  VARCHAR(5),
    DIRECCION        VARCHAR(300),
    CIUDAD           VARCHAR(100),
    CODIGO_POSTAL    VARCHAR(10),
    SEGURO_MEDICO    VARCHAR(200),
    TIPO_SEGURO      VARCHAR(50),
    FECHA_INICIO     DATE          NOT NULL,
    FECHA_FIN        DATE,
    ES_ACTUAL        BOOLEAN       NOT NULL   DEFAULT TRUE
);


CALL CONFORMED.SP_MERGE_SCD1_SCD2(
    'CONFORMED.DIM_PACIENTE',
    'SELECT
        ID_PACIENTE,
        NOMBRE,
        APELLIDO1 || '' '' || APELLIDO2  AS APELLIDOS,
        FECHA_NACIMIENTO,
        SEXO                             AS GENERO,
        TELEFONO_MOVIL                   AS TELEFONO,
        EMAIL,
        GRUPO_SANGUINEO,
        DIRECCION,
        CIUDAD,
        CODIGO_POSTAL,
        COMPANIA_SEGURO                  AS SEGURO_MEDICO,
        TIPO_COBERTURA                   AS TIPO_SEGURO
     FROM CLEANSED.PACIENTES',
    'ID_PACIENTE',
    'NOMBRE,APELLIDOS,FECHA_NACIMIENTO,GENERO,TELEFONO,EMAIL,GRUPO_SANGUINEO',
    'DIRECCION,CIUDAD,CODIGO_POSTAL,SEGURO_MEDICO,TIPO_SEGURO'
);
