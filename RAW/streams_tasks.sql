--este fichero es para crear los streams y tasks necesarios para la carga incremental 
--en la capa cleansed y tambien crear las tablas de cleansed a partir del esquema landing 

CREATE SCHEMA IF NOT EXISTS {esquema_raw};

CREATE TABLE IF NOT EXISTS {esquema_raw}.{nombre_tabla}
AS
SELECT * FROM {esquema_landing}.{nombre_tabla}
QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1;

CREATE OR REPLACE STREAM {esquema_raw}.STREAM_{nombre_tabla}
ON TABLE {esquema_landing}.{nombre_tabla};

CREATE OR REPLACE TASK {esquema_raw}.TASK_{nombre_tabla}
WAREHOUSE = COMPUTE_WH
SCHEDULE = '5 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('{esquema_raw}.STREAM_{nombre_tabla}')
AS
MERGE INTO {esquema_raw}.{nombre_tabla} AS target
USING (
    SELECT *, METADATA$ACTION AS ACCION_CDC
    FROM {esquema_raw}.STREAM_{nombre_tabla}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
) AS source
ON target.{clave_primaria} = source.{clave_primaria}
WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
{clausula_borrado_logico}
WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

ALTER TASK {esquema_raw}.TASK_{nombre_tabla} RESUME;
