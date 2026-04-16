-- 

================================================================
-- ESTO ES UN SCRIPT PARA LA CREACIÓN DE LAS TABLAS RAW - MEDICARE 
-- Base de datos: PROYECTO 
-- Schema: RAW 
-- Tipos de datos exactos según LANDING_MEDICARE de acuerdo a la consulta de INFORMATION_SCHEMA.COLUMNS (fichero COMPROBACIONES.SQL)
-- Incluye columnas originales + campos de control
-- ================================================================

-- ----------------------------------------------------------------
-- 1. CATEGORIA_EQUIPOS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_CATEGORIA_EQUIPOS (
    -- Columnas originales
    ID_CATEGORIA            NUMBER,
    CODIGO_CATEGORIA        TEXT,
    NOMBRE_CATEGORIA        TEXT,
    SUBCATEGORIA            TEXT,
    DESCRIPCION             TEXT,
    FECHA_CREACION          TIMESTAMP_NTZ,
    FECHA_MODIFICACION      TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN                 TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW             BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO      BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 2. CONSUMO_REPUESTOS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_CONSUMO_REPUESTOS (
    -- Columnas originales
    ID_CONSUMO                  NUMBER,
    ID_ORDEN                    NUMBER,
    ID_REPUESTO                 NUMBER,
    CANTIDAD                    NUMBER,
    PRECIO_UNITARIO_EN_MOMENTO  NUMBER,
    FECHA_CREACION              TIMESTAMP_NTZ,
    FECHA_MODIFICACION          TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN                     TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA              TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW                 BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO          BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 3. DEPARTAMENTOS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_DEPARTAMENTOS (
    -- Columnas originales
    ID_DEPARTAMENTO         NUMBER,
    CODIGO_DEPARTAMENTO     TEXT,
    NOMBRE_DEPARTAMENTO     TEXT,
    ID_DEPARTAMENTO_PADRE   NUMBER,
    NOMBRE_RESPONSABLE      TEXT,
    TELEFONO_DEPARTAMENTO   TEXT,
    EMAIL_DEPARTAMENTO      TEXT,
    ACTIVO                  BOOLEAN,
    FECHA_CREACION          TIMESTAMP_NTZ,
    FECHA_MODIFICACION      TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN                 TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW             BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO      BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 4. EQUIPOS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_EQUIPOS (
    -- Columnas originales
    ID_EQUIPO                   NUMBER,
    CODIGO_EQUIPO               TEXT,
    NOMBRE_EQUIPO               TEXT,
    DESCRIPCION                 TEXT,
    NUMERO_SERIE                TEXT,
    MODELO                      TEXT,
    ID_FABRICANTE               NUMBER,
    ID_CATEGORIA                NUMBER,
    ID_DEPARTAMENTO             NUMBER,
    ID_UBICACION                NUMBER,
    ESTADO_CODIGO               NUMBER,
    CLASE_RIESGO                TEXT,
    FECHA_ADQUISICION           DATE,
    FECHA_FIN_GARANTIA          DATE,
    PRECIO_ADQUISICION          NUMBER,
    VIDA_UTIL_ANIOS             NUMBER,
    FRECUENCIA_CALIBRACION_MESES NUMBER,
    CODIGO_CATALOGO_EXTERNO     TEXT,
    FECHA_CREACION              TIMESTAMP_NTZ,
    FECHA_MODIFICACION          TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN                     TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA              TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW                 BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO          BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 5. FABRICANTES
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_FABRICANTES (
    -- Columnas originales
    ID_FABRICANTE       NUMBER,
    CODIGO_FABRICANTE   TEXT,
    RAZON_SOCIAL        TEXT,
    PAIS_ORIGEN         TEXT,
    DIRECCION           TEXT,
    TELEFONO_CONTACTO   TEXT,
    EMAIL_CONTACTO      TEXT,
    SITIO_WEB           TEXT,
    CERTIFICACION_ISO   TEXT,
    FECHA_CREACION      TIMESTAMP_NTZ,
    FECHA_MODIFICACION  TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN             TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW         BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO  BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 6. ORDENES_MANTENIMIENTO
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_ORDENES_MANTENIMIENTO (
    -- Columnas originales
    ID_ORDEN                    NUMBER,
    NUMERO_ORDEN                TEXT,
    ID_EQUIPO                   NUMBER,
    ID_TECNICO                  NUMBER,
    TIPO_MANTENIMIENTO          TEXT,
    PRIORIDAD                   NUMBER,
    GRAVEDAD                    NUMBER,
    ES_CUBIERTO_POR_GARANTIA    BOOLEAN,
    REQUIERE_PARADA             BOOLEAN,
    FECHA_SOLICITUD             TIMESTAMP_NTZ,
    FECHA_INICIO_TRABAJO        TIMESTAMP_NTZ,
    FECHA_FIN_TRABAJO           TIMESTAMP_NTZ,
    HORAS_TRABAJADAS            NUMBER,
    DESCRIPCION_PROBLEMA        TEXT,
    DESCRIPCION_SOLUCION        TEXT,
    ESTADO_ORDEN                TEXT,
    FECHA_CREACION              TIMESTAMP_NTZ,
    FECHA_MODIFICACION          TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN                     TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA              TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW                 BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO          BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 7. PLANIFICACION_PREVENTIVOS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_PLANIFICACION_PREVENTIVOS (
    -- Columnas originales
    ID_PLANIFICACION    NUMBER,
    ID_EQUIPO           NUMBER,
    FECHA_PLANIFICADA   DATE,
    REALIZADO           BOOLEAN,
    ID_ORDEN_ASOCIADA   NUMBER,
    OBSERVACIONES       TEXT,
    FECHA_CREACION      TIMESTAMP_NTZ,
    FECHA_MODIFICACION  TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN             TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW         BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO  BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 8. REPUESTOS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_REPUESTOS (
    -- Columnas originales
    ID_REPUESTO         NUMBER,
    CODIGO_REPUESTO     TEXT,
    NOMBRE_REPUESTO     TEXT,
    DESCRIPCION         TEXT,
    ID_FABRICANTE       NUMBER,
    PRECIO_UNITARIO     NUMBER,
    STOCK_ACTUAL        NUMBER,
    STOCK_MINIMO        NUMBER,
    UNIDAD_MEDIDA       TEXT,
    FECHA_CREACION      TIMESTAMP_NTZ,
    FECHA_MODIFICACION  TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN             TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW         BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO  BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 9. TECNICOS
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_TECNICOS (
    -- Columnas originales
    ID_TECNICO          NUMBER,
    CODIGO_EMPLEADO     TEXT,
    NOMBRE_TECNICO      TEXT,
    ID_DEPARTAMENTO     NUMBER,
    ESPECIALIDAD        TEXT,
    NIVEL_CERTIFICACION NUMBER,
    ANIOS_EXPERIENCIA   NUMBER,
    TELEFONO_MOVIL      TEXT,
    EMAIL_CORPORATIVO   TEXT,
    TARIFA_HORA         NUMBER,
    ACTIVO              BOOLEAN,
    FECHA_CREACION      TIMESTAMP_NTZ,
    FECHA_MODIFICACION  TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN             TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW         BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO  BOOLEAN DEFAULT FALSE
);

-- ----------------------------------------------------------------
-- 10. UBICACIONES
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROYECTO.RAW.MEDICARE_UBICACIONES (
    -- Columnas originales
    ID_UBICACION        NUMBER,
    CODIGO_UBICACION    TEXT,
    EDIFICIO            TEXT,
    PLANTA              NUMBER,
    ALA                 TEXT,
    SALA                TEXT,
    TIPO_SALA           TEXT,
    CAPACIDAD           NUMBER,
    FECHA_CREACION      TIMESTAMP_NTZ,
    FECHA_MODIFICACION  TIMESTAMP_NTZ,
    -- Campos de control
    _ORIGEN             TEXT    DEFAULT 'MEDICARE',
    _FECHA_INGESTA      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _ACTIVO_RAW         BOOLEAN DEFAULT TRUE,
    _ES_BORRADO_LOGICO  BOOLEAN DEFAULT FALSE
);
