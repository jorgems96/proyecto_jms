--este fichero es para crear los streams y tasks necesarios para la carga incremental 
--en la capa cleansed y tambien crear las tablas de cleansed a partir del esquema landing 

CREATE SCHEMA IF NOT EXISTS {esquema_raw};
CREATE SCHEMA IF NOT EXISTS STREAMS;
CREATE SCHEMA IF NOT EXISTS TASKS;

CREATE TABLE IF NOT EXISTS {esquema_raw}.{nombre_tabla}
AS
SELECT * FROM {esquema_landing}.{nombre_tabla}
QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1;

CREATE OR REPLACE STREAM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}
ON TABLE {esquema_landing}.{nombre_tabla};

CREATE OR REPLACE TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla}
WAREHOUSE = COMPUTE_WH
SCHEDULE = '5 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}')
AS
MERGE INTO {esquema_raw}.{nombre_tabla} AS target
USING (
    SELECT *, METADATA$ACTION AS ACCION_CDC
    FROM STREAMS.STREAM_RAW_{nombre_proyecto}_{nombre_tabla}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
) AS source
ON target.{clave_primaria} = source.{clave_primaria}
WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
{clausula_borrado_logico}
WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

ALTER TASK TASKS.TASK_RAW_{nombre_proyecto}_{nombre_tabla} RESUME;
