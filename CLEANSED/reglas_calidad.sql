-- reglas_calidad.sql

-- Para crear la Tabla de configuracion de reglas de calidad para la capa CLEANSED.
-- Cada fila almacena un fragmento SQL listo para usar como condicion WHERE.
-- Las filas que cumplan TODAS las condiciones de su tabla van a CLEANSED.
-- Las que fallen alguna van a CLEANSED._ERRORS.
--
-- Tipos de condicion soportados:
--   not_null      → COL IS NOT NULL
--   positive      → COL > 0
--   non_negative  → COL >= 0
--   allowed_values→ COL IN ('v1', 'v2', ...)  /  COL IN (1, 2, ...)
--   regex         → REGEXP_LIKE(COL, 'patron')
--   range         → COL >= min AND COL <= max

CREATE SCHEMA IF NOT EXISTS CLEANSED;

CREATE OR REPLACE TABLE CLEANSED.REGLAS_CALIDAD (
    NOMBRE_TABLA VARCHAR(100)  NOT NULL, -- para identificar a qué tabla se aplica la regla
    COLUMNA      VARCHAR(100)  NOT NULL, -- para identificar a qué columna se refiere la regla (puede ser NULL si la regla no es sobre una columna específica)
    CONDICION    VARCHAR(1000) NOT NULL  -- fragmento SQL con la condición a evaluar
);

INSERT INTO CLEANSED.REGLAS_CALIDAD (NOMBRE_TABLA, COLUMNA, CONDICION) VALUES

-- ----------------------------------------------------------------
-- CATALOGO: productos_sanitarios
-- ----------------------------------------------------------------
('productos_sanitarios', 'CODIGO_PRODUCTO',       'CODIGO_PRODUCTO IS NOT NULL'),
('productos_sanitarios', 'NOMBRE_PRODUCTO',       'NOMBRE_PRODUCTO IS NOT NULL'),
('productos_sanitarios', 'CLASE_RIESGO',          'CLASE_RIESGO IN (''I'', ''IIa'', ''IIb'', ''III'')'),
('productos_sanitarios', 'VIDA_UTIL_ANIOS',       'VIDA_UTIL_ANIOS > 0'),
('productos_sanitarios', 'PRECIO_REFERENCIA_EUR', 'PRECIO_REFERENCIA_EUR > 0'),

-- ----------------------------------------------------------------
-- SGC: especialidades
-- ----------------------------------------------------------------
('especialidades', 'CODIGO_ESPECIALIDAD', 'CODIGO_ESPECIALIDAD IS NOT NULL'),
('especialidades', 'NOMBRE_ESPECIALIDAD', 'NOMBRE_ESPECIALIDAD IS NOT NULL'),

-- ----------------------------------------------------------------
-- SGC: medicos
-- ----------------------------------------------------------------
('medicos', 'CODIGO_MEDICO',    'CODIGO_MEDICO IS NOT NULL'),
('medicos', 'NOMBRE',           'NOMBRE IS NOT NULL'),
('medicos', 'APELLIDO1',        'APELLIDO1 IS NOT NULL'),
('medicos', 'NUMERO_COLEGIADO', 'NUMERO_COLEGIADO IS NOT NULL'),
('medicos', 'EMAIL',            'REGEXP_LIKE(EMAIL, ''^[^@]+@[^@]+\.[^@]+$'')'),

-- ----------------------------------------------------------------
-- SGC: pacientes
-- ----------------------------------------------------------------
('pacientes', 'NUMERO_HISTORIA',  'NUMERO_HISTORIA IS NOT NULL'),
('pacientes', 'NOMBRE',           'NOMBRE IS NOT NULL'),
('pacientes', 'APELLIDO1',        'APELLIDO1 IS NOT NULL'),
('pacientes', 'FECHA_NACIMIENTO', 'FECHA_NACIMIENTO IS NOT NULL'),
('pacientes', 'SEXO',             'SEXO IN (''M'', ''F'', ''O'')'),
('pacientes', 'GRUPO_SANGUINEO',  'GRUPO_SANGUINEO IN (''A+'', ''A-'', ''B+'', ''B-'', ''AB+'', ''AB-'', ''O+'', ''O-'')'),
('pacientes', 'TIPO_COBERTURA',   'TIPO_COBERTURA IN (''BAS'', ''COM'', ''PRE'')'),
('pacientes', 'EMAIL',            'REGEXP_LIKE(EMAIL, ''^[^@]+@[^@]+\.[^@]+$'')'),

-- ----------------------------------------------------------------
-- SGC: diagnosticos_cie10
-- ----------------------------------------------------------------
('diagnosticos_cie10', 'CODIGO_CIE10', 'CODIGO_CIE10 IS NOT NULL'),
('diagnosticos_cie10', 'DESCRIPCION',  'DESCRIPCION IS NOT NULL'),

-- ----------------------------------------------------------------
-- SGC: paciente_diagnostico
-- ----------------------------------------------------------------
('paciente_diagnostico', 'ID_PACIENTE',       'ID_PACIENTE IS NOT NULL'),
('paciente_diagnostico', 'ID_DIAGNOSTICO',    'ID_DIAGNOSTICO IS NOT NULL'),
('paciente_diagnostico', 'FECHA_DIAGNOSTICO', 'FECHA_DIAGNOSTICO IS NOT NULL'),

-- ----------------------------------------------------------------
-- SGC: ensayos_clinicos
-- ----------------------------------------------------------------
('ensayos_clinicos', 'CODIGO_ENSAYO',          'CODIGO_ENSAYO IS NOT NULL'),
('ensayos_clinicos', 'TITULO_ENSAYO',          'TITULO_ENSAYO IS NOT NULL'),
('ensayos_clinicos', 'FECHA_INICIO',           'FECHA_INICIO IS NOT NULL'),
('ensayos_clinicos', 'ESTADO_ENSAYO',          'ESTADO_ENSAYO IN (''PLN'', ''ACT'', ''COM'', ''SUS'')'),
('ensayos_clinicos', 'OBJETIVO_RECLUTAMIENTO', 'OBJETIVO_RECLUTAMIENTO > 0'),

-- ----------------------------------------------------------------
-- SGC: participacion_ensayos
-- ----------------------------------------------------------------
('participacion_ensayos', 'ID_ENSAYO',                  'ID_ENSAYO IS NOT NULL'),
('participacion_ensayos', 'ID_PACIENTE',                'ID_PACIENTE IS NOT NULL'),
('participacion_ensayos', 'FECHA_INICIO_PARTICIPACION', 'FECHA_INICIO_PARTICIPACION IS NOT NULL'),
('participacion_ensayos', 'FASE',                       'FASE IN (''F1'', ''F2'', ''F3'', ''F4'')'),
('participacion_ensayos', 'TIPO_CIEGO',                 'TIPO_CIEGO IN (''AB'', ''SC'', ''DC'')'),
('participacion_ensayos', 'TIPO_ALEATORIZACION',        'TIPO_ALEATORIZACION IN (''AL'', ''NA'')'),
('participacion_ensayos', 'GRUPO_ASIGNADO',             'GRUPO_ASIGNADO IN (''EXP'', ''CTR'', ''PLA'')'),
('participacion_ensayos', 'VIA_ADMINISTRACION',         'VIA_ADMINISTRACION IN (''ORL'', ''IV'', ''SC'', ''TOP'', ''INH'')'),

-- ----------------------------------------------------------------
-- SGC: visitas_ensayo
-- ----------------------------------------------------------------
('visitas_ensayo', 'ID_PARTICIPACION',        'ID_PARTICIPACION IS NOT NULL'),
('visitas_ensayo', 'FECHA_VISITA',            'FECHA_VISITA IS NOT NULL'),
('visitas_ensayo', 'NUMERO_VISITA',           'NUMERO_VISITA > 0'),
('visitas_ensayo', 'NIVEL_EFICACIA',          'NIVEL_EFICACIA >= 0.0 AND NIVEL_EFICACIA <= 1.0'),
('visitas_ensayo', 'DOSIS_ADMINISTRADA',      'DOSIS_ADMINISTRADA > 0'),
('visitas_ensayo', 'NUMERO_EFECTOS_ADVERSOS', 'NUMERO_EFECTOS_ADVERSOS >= 0'),

-- ----------------------------------------------------------------
-- SGC: monitorizaciones
-- ----------------------------------------------------------------
('monitorizaciones', 'ID_PACIENTE',          'ID_PACIENTE IS NOT NULL'),
('monitorizaciones', 'ID_MEDICO',            'ID_MEDICO IS NOT NULL'),
('monitorizaciones', 'CODIGO_EQUIPO',        'CODIGO_EQUIPO IS NOT NULL'),
('monitorizaciones', 'FECHA_MONITORIZACION', 'FECHA_MONITORIZACION IS NOT NULL'),

-- ----------------------------------------------------------------
-- SGC: lecturas_signos_vitales
-- ----------------------------------------------------------------
('lecturas_signos_vitales', 'ID_MONITORIZACION',   'ID_MONITORIZACION IS NOT NULL'),
('lecturas_signos_vitales', 'FRECUENCIA_CARDIACA', 'FRECUENCIA_CARDIACA >= 20 AND FRECUENCIA_CARDIACA <= 300'),
('lecturas_signos_vitales', 'PRESION_SISTOLICA',   'PRESION_SISTOLICA >= 40 AND PRESION_SISTOLICA <= 300'),
('lecturas_signos_vitales', 'PRESION_DIASTOLICA',  'PRESION_DIASTOLICA >= 20 AND PRESION_DIASTOLICA <= 200'),
('lecturas_signos_vitales', 'TEMPERATURA',         'TEMPERATURA >= 30 AND TEMPERATURA <= 45'),
('lecturas_signos_vitales', 'SATURACION_OXIGENO',  'SATURACION_OXIGENO >= 50 AND SATURACION_OXIGENO <= 100'),
('lecturas_signos_vitales', 'NIVEL_GLUCOSA',       'NIVEL_GLUCOSA >= 20 AND NIVEL_GLUCOSA <= 600'),

-- ----------------------------------------------------------------
-- SGEB: departamentos
-- ----------------------------------------------------------------
('departamentos', 'CODIGO_DEPARTAMENTO', 'CODIGO_DEPARTAMENTO IS NOT NULL'),
('departamentos', 'NOMBRE_DEPARTAMENTO', 'NOMBRE_DEPARTAMENTO IS NOT NULL'),
('departamentos', 'EMAIL_DEPARTAMENTO',  'REGEXP_LIKE(EMAIL_DEPARTAMENTO, ''^[^@]+@[^@]+\.[^@]+$'')'),

-- ----------------------------------------------------------------
-- SGEB: fabricantes
-- ----------------------------------------------------------------
('fabricantes', 'CODIGO_FABRICANTE', 'CODIGO_FABRICANTE IS NOT NULL'),
('fabricantes', 'RAZON_SOCIAL',      'RAZON_SOCIAL IS NOT NULL'),
('fabricantes', 'EMAIL_CONTACTO',    'REGEXP_LIKE(EMAIL_CONTACTO, ''^[^@]+@[^@]+\.[^@]+$'')'),

-- ----------------------------------------------------------------
-- SGEB: ubicaciones
-- ----------------------------------------------------------------
('ubicaciones', 'CODIGO_UBICACION', 'CODIGO_UBICACION IS NOT NULL'),
('ubicaciones', 'EDIFICIO',         'EDIFICIO IS NOT NULL'),
('ubicaciones', 'SALA',             'SALA IS NOT NULL'),
('ubicaciones', 'TIPO_SALA',        'TIPO_SALA IN (''Quirófano'', ''UCI'', ''Consulta'', ''Laboratorio'', ''Almacén'')'),
('ubicaciones', 'CAPACIDAD',        'CAPACIDAD > 0'),

-- ----------------------------------------------------------------
-- SGEB: equipos
-- ----------------------------------------------------------------
('equipos', 'CODIGO_EQUIPO',      'CODIGO_EQUIPO IS NOT NULL'),
('equipos', 'NOMBRE_EQUIPO',      'NOMBRE_EQUIPO IS NOT NULL'),
('equipos', 'NUMERO_SERIE',       'NUMERO_SERIE IS NOT NULL'),
('equipos', 'ID_FABRICANTE',      'ID_FABRICANTE IS NOT NULL'),
('equipos', 'ID_DEPARTAMENTO',    'ID_DEPARTAMENTO IS NOT NULL'),
('equipos', 'ID_UBICACION',       'ID_UBICACION IS NOT NULL'),
('equipos', 'ESTADO_CODIGO',      'ESTADO_CODIGO IN (1, 2, 3, 4)'),
('equipos', 'CLASE_RIESGO',       'CLASE_RIESGO IN (''I'', ''IIa'', ''IIb'', ''III'')'),
('equipos', 'PRECIO_ADQUISICION', 'PRECIO_ADQUISICION > 0'),

-- ----------------------------------------------------------------
-- SGEB: tecnicos
-- ----------------------------------------------------------------
('tecnicos', 'CODIGO_EMPLEADO',     'CODIGO_EMPLEADO IS NOT NULL'),
('tecnicos', 'NOMBRE_TECNICO',      'NOMBRE_TECNICO IS NOT NULL'),
('tecnicos', 'ID_DEPARTAMENTO',     'ID_DEPARTAMENTO IS NOT NULL'),
('tecnicos', 'NIVEL_CERTIFICACION', 'NIVEL_CERTIFICACION IN (1, 2, 3, 4)'),
('tecnicos', 'TARIFA_HORA',         'TARIFA_HORA > 0'),
('tecnicos', 'EMAIL_CORPORATIVO',   'REGEXP_LIKE(EMAIL_CORPORATIVO, ''^[^@]+@[^@]+\.[^@]+$'')'),

-- ----------------------------------------------------------------
-- SGEB: ordenes_mantenimiento
-- ----------------------------------------------------------------
('ordenes_mantenimiento', 'NUMERO_ORDEN',       'NUMERO_ORDEN IS NOT NULL'),
('ordenes_mantenimiento', 'ID_EQUIPO',          'ID_EQUIPO IS NOT NULL'),
('ordenes_mantenimiento', 'ID_TECNICO',         'ID_TECNICO IS NOT NULL'),
('ordenes_mantenimiento', 'TIPO_MANTENIMIENTO', 'TIPO_MANTENIMIENTO IN (''PREV'', ''CORR'', ''CALIB'', ''INSP'')'),
('ordenes_mantenimiento', 'PRIORIDAD',          'PRIORIDAD >= 1 AND PRIORIDAD <= 4'),
('ordenes_mantenimiento', 'GRAVEDAD',           'GRAVEDAD >= 1 AND GRAVEDAD <= 3'),
('ordenes_mantenimiento', 'HORAS_TRABAJADAS',   'HORAS_TRABAJADAS > 0'),

-- ----------------------------------------------------------------
-- SGEB: consumo_repuestos
-- ----------------------------------------------------------------
('consumo_repuestos', 'ID_ORDEN',                   'ID_ORDEN IS NOT NULL'),
('consumo_repuestos', 'ID_REPUESTO',                'ID_REPUESTO IS NOT NULL'),
('consumo_repuestos', 'CANTIDAD',                   'CANTIDAD > 0'),
('consumo_repuestos', 'PRECIO_UNITARIO_EN_MOMENTO', 'PRECIO_UNITARIO_EN_MOMENTO > 0'),

-- ----------------------------------------------------------------
-- SGEB: repuestos
-- ----------------------------------------------------------------
('repuestos', 'CODIGO_REPUESTO', 'CODIGO_REPUESTO IS NOT NULL'),
('repuestos', 'NOMBRE_REPUESTO', 'NOMBRE_REPUESTO IS NOT NULL'),
('repuestos', 'PRECIO_UNITARIO', 'PRECIO_UNITARIO > 0'),

-- ----------------------------------------------------------------
-- SGEB: categoria_equipos
-- ----------------------------------------------------------------
('categoria_equipos', 'CODIGO_CATEGORIA', 'CODIGO_CATEGORIA IS NOT NULL'),
('categoria_equipos', 'NOMBRE_CATEGORIA', 'NOMBRE_CATEGORIA IS NOT NULL'),

-- ----------------------------------------------------------------
-- SGEB: planificacion_preventivos
-- ----------------------------------------------------------------
('planificacion_preventivos', 'ID_EQUIPO',         'ID_EQUIPO IS NOT NULL'),
('planificacion_preventivos', 'FECHA_PLANIFICADA', 'FECHA_PLANIFICADA IS NOT NULL')
;
