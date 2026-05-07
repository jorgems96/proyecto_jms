-- [SETUP]
--este fichero es para crear los streams y tasks necesarios para la carga incremental 
--en la capa cleansed y tambien crear las tablas de cleansed a partir de las RAW




CREATE SCHEMA IF NOT EXISTS {esquema_cleansed};
CREATE SCHEMA IF NOT EXISTS STREAMS;
CREATE SCHEMA IF NOT EXISTS TASKS;

CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}
AS SELECT * FROM {esquema_raw}.{nombre_tabla}
WHERE {condicion_valida_inicial};

CREATE TABLE IF NOT EXISTS {esquema_cleansed}.{nombre_tabla}_ERRORS
AS SELECT * FROM {esquema_raw}.{nombre_tabla}
WHERE {condicion_invalida_inicial};

CREATE OR REPLACE STREAM {nombre_stream} ON TABLE {esquema_raw}.{nombre_tabla};

-- [TASK]
CREATE OR REPLACE TASK {nombre_task}
WAREHOUSE = COMPUTE_WH
SCHEDULE = '5 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('{nombre_stream}')
AS
BEGIN
  -- Transaccion explicita para que ambos MERGEs lean el mismo snapshot del Stream.
  -- Sin ella, Snowflake Scripting hace auto-commit tras el primer MERGE y el Stream
  -- queda vacio cuando llega el segundo, perdiendo las filas invalidas.
  BEGIN TRANSACTION; -- esto es necesario para asegurar que ambos MERGE lean el mismo snapshot del Stream

  MERGE INTO {esquema_cleansed}.{nombre_tabla} AS target
  USING (
      SELECT *, METADATA$ACTION AS ACCION_CDC
      FROM {nombre_stream}
      WHERE {condicion_valida_merge}
      QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1
  ) AS source
  ON target.{clave_primaria} = source.{clave_primaria}
  WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
  WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
  WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

  MERGE INTO {esquema_cleansed}.{nombre_tabla}_ERRORS AS target
  USING (
      SELECT *, METADATA$ACTION AS ACCION_CDC
      FROM {nombre_stream}
      WHERE {condicion_invalida_merge}
      QUALIFY ROW_NUMBER() OVER (PARTITION BY {clave_primaria} ORDER BY {orden_cdc}) = 1 
  ) AS source
  ON target.{clave_primaria} = source.{clave_primaria}
  WHEN MATCHED AND source.ACCION_CDC = 'DELETE' THEN DELETE
  WHEN MATCHED AND source.ACCION_CDC = 'INSERT' THEN UPDATE SET {update_set}
  WHEN NOT MATCHED AND source.ACCION_CDC = 'INSERT' THEN INSERT ({insert_cols}) VALUES ({insert_vals});

  COMMIT;
END



-- Desplegar todo
EXECUTE TASK TASKS.TASK_CONFORMED_ROOT;

-- Solo tres dimensiones concretas
EXECUTE TASK TASKS.TASK_DIM_MEDICO;
EXECUTE TASK TASKS.TASK_DIM_PACIENTE;
EXECUTE TASK TASKS.TASK_DIM_ENSAYO;

-- Solo un hecho (asumiendo dims ya cargadas)
EXECUTE TASK TASKS.TASK_FACT_ENSAYOS_CLINICOS;


