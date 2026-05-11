-- mantenimiento_equipos.sql
-- Definicion de referencia de OPTIMIZED.MANTENIMIENTO_EQUIPOS
-- Este fichero es solo documentacion/lectura.
-- La vista se crea o actualiza llamando a: CALL OPTIMIZED.SP_DEPLOY_OPTIMIZED()  (FASE 5)

CREATE OR REPLACE VIEW OPTIMIZED.MANTENIMIENTO_EQUIPOS AS
SELECT
    -- Identificador de la orden
    f.ID_ORDEN,

    -- Fecha de la orden
    fe.FECHA,
    fe.ANIO,
    fe.SEMESTRE,
    fe.TRIMESTRE,
    fe.MES,
    fe.NOMBRE_MES,
    fe.SEMANA_ANIO,
    fe.DIA,
    fe.NOMBRE_DIA,
    fe.ES_FIN_SEMANA,

    -- Equipo intervenido (version SCD2 activa)
    eq.NOMBRE_EQUIPO,
    eq.NUMERO_SERIE,
    eq.MODELO,
    eq.CLASE_RIESGO,
    eq.ESTADO_EQUIPO,
    eq.DEPARTAMENTO_ACTUAL      AS DEPARTAMENTO_EQUIPO,
    eq.UBICACION_ACTUAL         AS UBICACION_EQUIPO,
    eq.FECHA_ADQUISICION,
    eq.FECHA_FIN_GARANTIA,

    -- Tecnico responsable (version SCD2 activa)
    tc.NOMBRE                   AS NOMBRE_TECNICO,
    tc.APELLIDOS                AS APELLIDOS_TECNICO,
    tc.ESPECIALIDAD             AS ESPECIALIDAD_TECNICO,
    tc.NIVEL_CERTIFICACION,
    tc.ANIOS_EXPERIENCIA,

    -- Departamento de la orden
    dp.NOMBRE_DEPARTAMENTO,
    dp.NIVEL_JERARQUIA          AS NIVEL_JERARQUIA_DEPARTAMENTO,

    -- Ubicacion de la orden
    ub.EDIFICIO,
    ub.PLANTA,
    ub.ALA,
    ub.SALA,
    ub.TIPO_SALA,

    -- Fabricante del equipo
    fa.NOMBRE_FABRICANTE,
    fa.PAIS_ORIGEN,
    fa.CERTIFICACION_ISO,

    -- Perfil del mantenimiento
    pm.TIPO_MANTENIMIENTO,
    pm.PRIORIDAD,
    pm.GRAVEDAD,
    pm.ES_GARANTIA,
    pm.REQUIERE_PARADA_EQUIPO,

    -- Medidas de la orden
    f.HORAS_TRABAJADAS,
    f.TARIFA_HORA,
    f.COSTO_REPUESTOS,
    f.COSTO_MANO_OBRA,
    f.COSTO_TOTAL,
    f.DURACION_HORAS,
    f.NUMERO_PIEZAS_REEMPLAZADAS,
    f.INDICADOR_REINCIDENCIA

FROM CONFORMED.FACT_MANTENIMIENTO_EQUIPOS f
JOIN CONFORMED.DIM_FECHA                fe ON fe.SK_FECHA                = f.SK_FECHA
JOIN CONFORMED.DIM_EQUIPO               eq ON eq.SK_EQUIPO               = f.SK_EQUIPO               AND eq.ES_ACTUAL = TRUE
JOIN CONFORMED.DIM_TECNICO              tc ON tc.SK_TECNICO              = f.SK_TECNICO              AND tc.ES_ACTUAL = TRUE
JOIN CONFORMED.DIM_DEPARTAMENTO         dp ON dp.SK_DEPARTAMENTO         = f.SK_DEPARTAMENTO
JOIN CONFORMED.DIM_UBICACION            ub ON ub.SK_UBICACION            = f.SK_UBICACION
JOIN CONFORMED.DIM_FABRICANTE           fa ON fa.SK_FABRICANTE           = f.SK_FABRICANTE
JOIN CONFORMED.DIM_PERFIL_MANTENIMIENTO pm ON pm.SK_PERFIL_MANTENIMIENTO = f.SK_PERFIL_MANTENIMIENTO;
