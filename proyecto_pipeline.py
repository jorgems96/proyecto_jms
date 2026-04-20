# ---------------------------------------------------------------
# proyecto_pipeline.py
# Pipeline de ingesta incremental hacia Snowflake (capa LANDING)
# Fuentes: MEDICARE (SQL Server), NEXTBIO (PostgreSQL), CSV (Azure Blob)
# ---------------------------------------------------------------

import os
import io
import csv
from datetime import datetime
import logging

import dlt
from dlt.sources.sql_database import sql_table
import sqlalchemy as sa
from azure.storage.blob import BlobServiceClient
from concurrent.futures import ProcessPoolExecutor, as_completed

#Descomentar para silenciar logs amarillos de dlt
logging.getLogger("dlt").setLevel(logging.ERROR)   



from datos import (
    SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_ROLE,
    TABLAS_MEDICARE, SCHEMA_LANDING_MEDICARE, CAMPO_CURSOR_MEDICARE_SNOWFLAKE, CAMPO_CURSOR_MEDICARE_ORIGEN,
    TABLAS_NEXTBIO, SCHEMA_LANDING_NEXTBIO, CAMPO_CURSOR_NEXTBIO,
    SCHEMA_LANDING_PRODUCTOS, TABLA_PRODUCTOS,
    AZURE_ACCOUNT_NAME, AZURE_CONTAINER_NAME, AZURE_SAS_TOKEN,
)

# ---------------------------------------------------------------
# CONEXIONES Y HELPERS
# ---------------------------------------------------------------
def get_snowflake_connection():
    import snowflake.connector
    return snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        role=SNOWFLAKE_ROLE
    )

def get_watermark(sf_conn, schema, tabla_landing, campo_cursor):
    cursor = sf_conn.cursor()
    try:
        cursor.execute(f"SELECT COALESCE(MAX({campo_cursor}), '1900-01-01'::TIMESTAMP) FROM {SNOWFLAKE_DATABASE}.{schema}.{tabla_landing.upper()}")
        result = cursor.fetchone()[0]
        if isinstance(result, str):
            return datetime.strptime(result[:19], '%Y-%m-%d %H:%M:%S')
        return result if result else datetime(1900, 1, 1)
    except Exception:
        return datetime(1900, 1, 1)
    finally:
        cursor.close()

# ---------------------------------------------------------------
# FUENTE 1: MEDICARE (Azure SQL Server)
# ---------------------------------------------------------------
def load_medicare_landing() -> None:
    inicio = datetime.now()
    print(f"\n{'='*60}\n[MEDICARE] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")

    sf_conn = get_snowflake_connection()

    pipeline = dlt.pipeline(
        pipeline_name="medicare_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_MEDICARE,
        pipelines_dir=r"C:\dlt_temp\medicare"
    )

    print("\n[MEDICARE] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in TABLAS_MEDICARE.items():
        watermark = get_watermark(sf_conn, SCHEMA_LANDING_MEDICARE, tabla_landing, CAMPO_CURSOR_MEDICARE_SNOWFLAKE)
        print(f"  [MEDICARE] -> Tabla: {tabla_origen} | Watermark: {watermark}")

        resource = sql_table(
            credentials=dlt.secrets["conexion_medicare"],
            table=tabla_origen,
            incremental=dlt.sources.incremental(
                CAMPO_CURSOR_MEDICARE_ORIGEN,
                initial_value=watermark,
                last_value_func=max
            )
        )

        run_pipeline_seguro(pipeline, [resource], write_disposition="append")

        try:
            conteos = pipeline.last_trace.last_normalize_info.row_counts
            filas_cargadas = sum(filas for tabla, filas in conteos.items() if not tabla.startswith("_dlt"))
        except (AttributeError, TypeError):
            filas_cargadas = 0

        if filas_cargadas > 0:
            print(f"   [MEDICARE] OK: Se han cargado {filas_cargadas} filas nuevas en {tabla_origen}.")
        else:
            print(f"   [MEDICARE] OK: No hay cambios en la tabla {tabla_origen}.")

    sf_conn.close()
    fin = datetime.now()
    print(f"\n[MEDICARE] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')} | Duracion total: {fin - inicio}\n{'='*60}")

# ---------------------------------------------------------------
# FUENTE 2: NEXTBIO (PostgreSQL)
# ---------------------------------------------------------------
def load_nextbio_landing() -> None:
    inicio = datetime.now()
    print(f"\n{'='*60}\n[NEXTBIO] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")

    sf_conn = get_snowflake_connection()

    pipeline = dlt.pipeline(
        pipeline_name="nextbio_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_NEXTBIO,
        pipelines_dir=r"C:\dlt_temp\nextbio"
    )

    # Pipeline separado para lecturas_signos_vitales (sin estado de deduplicacion)
    pipeline_lecturas = dlt.pipeline(
        pipeline_name="nextbio_lecturas_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_NEXTBIO,
        pipelines_dir=r"C:\dlt_temp\nextbio_lecturas"
    )

    print("\n[NEXTBIO] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in TABLAS_NEXTBIO.items():
        watermark = get_watermark(sf_conn, SCHEMA_LANDING_NEXTBIO, tabla_landing, CAMPO_CURSOR_NEXTBIO)
        print(f"  [NEXTBIO] -> Tabla: {tabla_origen} | Watermark: {watermark}")

        if tabla_origen == "lecturas_signos_vitales":
            # Esta tabla tiene 876.830 registros con la misma fecha_modificacion
            # dlt no puede guardar el estado de deduplicacion (supera 16MB en Snowflake)
            # Solucion: lectura directa con SQLAlchemy y carga con dlt sin incremental
            engine = sa.create_engine(dlt.secrets["conexion_nextbio"])
            with engine.connect() as conn:
                query = sa.text(f"SELECT * FROM lecturas_signos_vitales WHERE {CAMPO_CURSOR_NEXTBIO} > :wm")
                result = conn.execute(query, {"wm": watermark})
                filas = [dict(row._mapping) for row in result]
            engine.dispose()

            if len(filas) > 0:
                pipeline_lecturas.run(filas, table_name=tabla_origen, write_disposition="append")
                print(f"  [NEXTBIO]   OK: Se han cargado {len(filas)} filas nuevas en {tabla_origen}.")
            else:
                print(f"  [NEXTBIO]   OK: No hay cambios en la tabla {tabla_origen}.")
        else:
            resource = sql_table(
                credentials=dlt.secrets["conexion_nextbio"],
                table=tabla_origen,
                incremental=dlt.sources.incremental(
                    CAMPO_CURSOR_NEXTBIO,
                    initial_value=watermark,
                    last_value_func=max
                )
            )
            run_pipeline_seguro(pipeline, [resource], write_disposition="append")

            try:
                conteos = pipeline.last_trace.last_normalize_info.row_counts
                filas_cargadas = sum(filas for tabla, filas in conteos.items() if not tabla.startswith("_dlt"))
            except (AttributeError, TypeError):
                filas_cargadas = 0

            if filas_cargadas > 0:
                print(f"  [NEXTBIO]   OK: Se han cargado {filas_cargadas} filas nuevas en {tabla_origen}.")
            else:
                print(f"  [NEXTBIO]   OK: No hay cambios en la tabla {tabla_origen}.")

    sf_conn.close()
    fin = datetime.now()
    print(f"\n[NEXTBIO] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')} | Duracion total: {fin - inicio}\n{'='*60}")

# ---------------------------------------------------------------
# FUENTE 3: CSV PRODUCTOS SANITARIOS (Azure Blob Storage)
# ---------------------------------------------------------------
def load_productos_landing() -> None:
    inicio = datetime.now()
    print(f"\n{'='*60}\n[PRODUCTOS CSV] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")

    sf_conn = get_snowflake_connection()
    cursor = sf_conn.cursor()
    try:
        cursor.execute(f"SELECT DISTINCT FICHERO_ORIGEN FROM {SNOWFLAKE_DATABASE}.{SCHEMA_LANDING_PRODUCTOS}.{TABLA_PRODUCTOS}")
        ficheros_procesados = {row[0] for row in cursor.fetchall()}
    except Exception:
        ficheros_procesados = set()
    finally:
        cursor.close()

    blob_service = BlobServiceClient(
        account_url=f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=AZURE_SAS_TOKEN
    )
    container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)
    blobs = [b.name for b in container_client.list_blobs() if b.name.endswith(".csv")]

    ficheros_nuevos = [b for b in blobs if b not in ficheros_procesados]
    print(f"\n[PRODUCTOS CSV] Ficheros detectados: {len(blobs)} | Ficheros nuevos a procesar: {len(ficheros_nuevos)}")

    if not ficheros_nuevos:
        print("     [PRODUCTOS CSV] No hay ficheros nuevos que procesar.")
        sf_conn.close()
        fin = datetime.now()
        print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')} | Duracion total: {fin - inicio}\n{'='*60}")
        return

    pipeline = dlt.pipeline(
        pipeline_name="productos_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_PRODUCTOS,
        pipelines_dir=r"C:\dlt_temp\productos"
    )

    for fichero in ficheros_nuevos:
        print(f"\n  [PRODUCTOS CSV] -> Procesando: {fichero}")
        blob_client = blob_service.get_blob_client(container=AZURE_CONTAINER_NAME, blob=fichero)

        content = blob_client.download_blob().readall().decode("utf-8")
        fichero_csv = io.StringIO(content)
        reader = csv.DictReader(fichero_csv, delimiter=";")

        datos = []
        for fila in reader:
            fila["FICHERO_ORIGEN"] = fichero
            datos.append(dict(fila))

        run_pipeline_seguro(pipeline, datos, table_name=TABLA_PRODUCTOS, write_disposition="append")

        try:
            conteos = pipeline.last_trace.last_normalize_info.row_counts
            filas_cargadas = sum(filas for tabla, filas in conteos.items() if not tabla.startswith("_dlt"))
        except (AttributeError, TypeError):
            filas_cargadas = len(datos)

        print(f"  [PRODUCTOS CSV]   OK: Se han cargado {filas_cargadas} filas nuevas del fichero {fichero}.")

    sf_conn.close()
    fin = datetime.now()
    print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')} | Duracion total: {fin - inicio}\n{'='*60}")



# Helper para reintentos automáticos en caso de que me bloquee los archivos el Windows Defender
def run_pipeline_seguro(pipeline, data, **kwargs):
    """Ejecuta pipeline.run con reintentos automáticos para WinError 5"""
    import time
    for intento in range(3):
        try:
            return pipeline.run(data, **kwargs)
        except Exception as e:
            if "WinError 5" in str(e) and intento < 2:
                print(f"     [!] Windows bloqueó archivo. Reintento {intento+1}/3...")
                time.sleep(3)
            else:
                raise






# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
if __name__ == '__main__':
    funciones = [
        load_medicare_landing,
        load_nextbio_landing,
        load_productos_landing,
    ]

    print("\n INICIANDO PIPELINE DE EXTRACCION (PARALELO CON 3 PROCESOS)...")
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(f): f.__name__ for f in funciones}
        for future in as_completed(futures):
            nombre = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[ERROR] {nombre} falló: {e}")
