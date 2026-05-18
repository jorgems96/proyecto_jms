-- ensayos_clinicos.sql
-- Definicion de referencia de OPTIMIZED.ENSAYOS_CLINICOS
-- Este fichero es solo documentacion/lectura.
-- La vista se crea o actualiza llamando a: CALL OPTIMIZED.SP_DEPLOY_OPTIMIZED()  (FASE 5)


--ESTE FICHERO NO EJECUTA NI CREA NADA, ES SIMPLE DOCUMENTACION DE APOYO 
--PARA ENTENDER LAS REFERENCIAS DE LOS NOMBRES DE CAMPOS EN LA VISTA OPTIMIZED.ENSAYOS_CLINICOS
CREATE OR REPLACE VIEW OPTIMIZED.ENSAYOS_CLINICOS AS
SELECT
    -- Identificador de la visita
    f.ID_VISITA,

    -- Fecha de la visita
    fv.FECHA                    AS FECHA_VISITA,
    fv.ANIO                     AS ANIO_VISITA,
    fv.TRIMESTRE                AS TRIMESTRE_VISITA,
    fv.MES                      AS MES_VISITA,
    fv.NOMBRE_MES               AS NOMBRE_MES_VISITA,

    -- Fechas de participacion del paciente en el ensayo
    fi.FECHA                    AS FECHA_INICIO_PARTICIPACION,
    ff.FECHA                    AS FECHA_FIN_PARTICIPACION,  -- NULL si el ensayo sigue activo

    -- Ensayo clinico
    en.CODIGO_ENSAYO,
    en.NOMBRE_ENSAYO,
    en.PATROCINADOR,
    en.ESTADO_ENSAYO,
    en.MOLECULA_FARMACO,
    en.OBJETIVO_PRINCIPAL,
    en.FECHA_INICIO_ENSAYO,
    en.FECHA_FIN_PREVISTA,

    -- Paciente (version SCD2 activa)
    pa.NOMBRE                   AS NOMBRE_PACIENTE,
    pa.APELLIDOS                AS APELLIDOS_PACIENTE,
    pa.GENERO,
    pa.FECHA_NACIMIENTO,
    pa.GRUPO_SANGUINEO,

    -- Medico responsable (version SCD2 activa)
    me.NOMBRE                   AS NOMBRE_MEDICO,
    me.APELLIDOS                AS APELLIDOS_MEDICO,
    me.ESPECIALIDAD             AS ESPECIALIDAD_MEDICO,

    -- Diagnostico
    di.CODIGO_CIE10,
    di.DESCRIPCION_DIAGNOSTICO,
    di.CATEGORIA                AS CATEGORIA_DIAGNOSTICO,
    di.ES_CRONICO,

    -- Departamento
    dp.NOMBRE_DEPARTAMENTO,

    -- Perfil del ensayo (diseno metodologico)
    pe.FASE_ENSAYO,
    pe.TIPO_CIEGO,
    pe.TIPO_ALEATORIZACION,
    pe.GRUPO_TRATAMIENTO,
    pe.VIA_ADMINISTRACION,

    -- Medidas de la visita
    f.DOSIS_ADMINISTRADA,
    f.UNIDAD_DOSIS,
    f.NUMERO_EFECTOS_ADVERSOS,
    f.RESULTADO_MEDICION_PRINCIPAL,
    f.RESULTADO_MEDICION_SECUNDARIA,
    f.NIVEL_EFICACIA

FROM CONFORMED.FACT_ENSAYOS_CLINICOS f
JOIN      CONFORMED.DIM_FECHA         fv ON fv.SK_FECHA         = f.SK_FECHA
JOIN      CONFORMED.DIM_FECHA         fi ON fi.SK_FECHA         = f.SK_FECHA_INICIO
LEFT JOIN CONFORMED.DIM_FECHA         ff ON ff.SK_FECHA         = f.SK_FECHA_FIN
JOIN      CONFORMED.DIM_ENSAYO        en ON en.SK_ENSAYO        = f.SK_ENSAYO
JOIN      CONFORMED.DIM_PACIENTE      pa ON pa.SK_PACIENTE      = f.SK_PACIENTE      AND pa.ES_ACTUAL = TRUE
JOIN      CONFORMED.DIM_MEDICO        me ON me.SK_MEDICO        = f.SK_MEDICO        AND me.ES_ACTUAL = TRUE
JOIN      CONFORMED.DIM_DIAGNOSTICO   di ON di.SK_DIAGNOSTICO   = f.SK_DIAGNOSTICO
JOIN      CONFORMED.DIM_DEPARTAMENTO  dp ON dp.SK_DEPARTAMENTO  = f.SK_DEPARTAMENTO
JOIN      CONFORMED.DIM_PERFIL_ENSAYO pe ON pe.SK_PERFIL_ENSAYO = f.SK_PERFIL_ENSAYO;
