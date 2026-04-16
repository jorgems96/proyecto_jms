--Aqui van los procedimientos almacenados para la carga incremental desde LANDING a RAW de las tablas de MEDICARE 

-- ================================================================
-- PROCEDIMIENTO ALMACENADO: LANDING → RAW
-- Tabla: MEDICARE_DEPARTAMENTOS
-- Lógica: MERGE incremental usando FECHA_MODIFICACION como watermark
-- ================================================================

CREATE OR REPLACE PROCEDURE PROYECTO.RAW.SP_LANDING_TO_RAW_MEDICARE_DEPARTAMENTOS()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    v_filas_insertadas  INTEGER DEFAULT 0;
    v_filas_actualizadas INTEGER DEFAULT 0;
    v_mensaje           VARCHAR;
BEGIN

    -- MERGE: inserta nuevos registros o actualiza los modificados
    MERGE INTO PROYECTO.RAW.MEDICARE_DEPARTAMENTOS AS target
    USING (
        SELECT
            ID_DEPARTAMENTO,
            CODIGO_DEPARTAMENTO,
            NOMBRE_DEPARTAMENTO,
            ID_DEPARTAMENTO_PADRE,
            NOMBRE_RESPONSABLE,
            TELEFONO_DEPARTAMENTO,
            EMAIL_DEPARTAMENTO,
            ACTIVO,
            FECHA_CREACION,
            FECHA_MODIFICACION
        FROM PROYECTO.LANDING_MEDICARE.DEPARTAMENTOS
        WHERE FECHA_MODIFICACION > (
            -- Watermark: última fecha de modificación ya cargada en RAW
            SELECT COALESCE(MAX(FECHA_MODIFICACION), '1900-01-01')
            FROM PROYECTO.RAW.MEDICARE_DEPARTAMENTOS
        )
    ) AS source
    ON target.ID_DEPARTAMENTO = source.ID_DEPARTAMENTO

    -- Si el registro existe y ha sido modificado → UPDATE
    WHEN MATCHED AND source.FECHA_MODIFICACION > target.FECHA_MODIFICACION THEN
        UPDATE SET
            target.CODIGO_DEPARTAMENTO     = source.CODIGO_DEPARTAMENTO,
            target.NOMBRE_DEPARTAMENTO     = source.NOMBRE_DEPARTAMENTO,
            target.ID_DEPARTAMENTO_PADRE   = source.ID_DEPARTAMENTO_PADRE,
            target.NOMBRE_RESPONSABLE      = source.NOMBRE_RESPONSABLE,
            target.TELEFONO_DEPARTAMENTO   = source.TELEFONO_DEPARTAMENTO,
            target.EMAIL_DEPARTAMENTO      = source.EMAIL_DEPARTAMENTO,
            target.ACTIVO                  = source.ACTIVO,
            target.FECHA_CREACION          = source.FECHA_CREACION,
            target.FECHA_MODIFICACION      = source.FECHA_MODIFICACION,
            target._FECHA_INGESTA          = CURRENT_TIMESTAMP(),
            target._ACTIVO_RAW             = TRUE,
            target._ES_BORRADO_LOGICO      = FALSE

    -- Si el registro no existe → INSERT
    WHEN NOT MATCHED THEN
        INSERT (
            ID_DEPARTAMENTO,
            CODIGO_DEPARTAMENTO,
            NOMBRE_DEPARTAMENTO,
            ID_DEPARTAMENTO_PADRE,
            NOMBRE_RESPONSABLE,
            TELEFONO_DEPARTAMENTO,
            EMAIL_DEPARTAMENTO,
            ACTIVO,
            FECHA_CREACION,
            FECHA_MODIFICACION,
            _ORIGEN,
            _FECHA_INGESTA,
            _ACTIVO_RAW,
            _ES_BORRADO_LOGICO
        )
        VALUES (
            source.ID_DEPARTAMENTO,
            source.CODIGO_DEPARTAMENTO,
            source.NOMBRE_DEPARTAMENTO,
            source.ID_DEPARTAMENTO_PADRE,
            source.NOMBRE_RESPONSABLE,
            source.TELEFONO_DEPARTAMENTO,
            source.EMAIL_DEPARTAMENTO,
            source.ACTIVO,
            source.FECHA_CREACION,
            source.FECHA_MODIFICACION,
            'MEDICARE',
            CURRENT_TIMESTAMP(),
            TRUE,
            FALSE
        );

    -- Capturar métricas
    v_filas_insertadas   := SQLROWCOUNT;
    v_mensaje := 'SP_LANDING_TO_RAW_MEDICARE_DEPARTAMENTOS ejecutado correctamente. ' ||
                 'Filas procesadas: ' || v_filas_insertadas::VARCHAR;

    RETURN v_mensaje;

EXCEPTION
    WHEN OTHER THEN
        RETURN 'ERROR en SP_LANDING_TO_RAW_MEDICARE_DEPARTAMENTOS: ' || SQLERRM;
END;
$$;

-- ================================================================
-- EJECUTAR EL PROCEDIMIENTO
-- ================================================================
CALL PROYECTO.RAW.SP_LANDING_TO_RAW_MEDICARE_DEPARTAMENTOS();




