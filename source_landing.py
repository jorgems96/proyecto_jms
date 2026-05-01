# Source_a_Landing.py
import io
import csv
from datetime import datetime

import dlt
import sqlalchemy as sa
from azure.storage.blob import BlobServiceClient
from concurrent.futures import ProcessPoolExecutor, as_completed

from conexiones import get_snowflake_connection
from datos import (
    TABLAS_MEDICARE, SCHEMA_LANDING_MEDICARE, CAMPO_CURSOR_MEDICARE_ORIGEN,
    TABLAS_NEXTBIO, SCHEMA_LANDING_NEXTBIO, CAMPO_CURSOR_NEXTBIO,
    SCHEMA_LANDING_PRODUCTOS, TABLA_PRODUCTOS,
    AZURE_CONTAINER_NAME
)
from utils import get_watermark, fetch_filas_incremental, get_column_hints


# ---------------------------------------------------------------
# FUENTE 1: MEDICARE (Azure SQL Server)
# ---------------------------------------------------------------
def load_medicare_landing() -> None:
    inicio = datetime.now()
    print(f"\n{'='*60}\n[MEDICARE] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")

    pipeline = dlt.pipeline(
        pipeline_name="medicare_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_MEDICARE,
        pipelines_dir=r"C:\dlt_temp\medicare"
    )

    sf_conn = get_snowflake_connection()
    engine = sa.create_engine(dlt.secrets["conexion_medicare"])
    print("\n[MEDICARE] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in TABLAS_MEDICARE.items(): 
        watermark = get_watermark(sf_conn, SCHEMA_LANDING_MEDICARE, tabla_landing, CAMPO_CURSOR_MEDICARE_ORIGEN)
        print(f"  [MEDICARE] -> Tabla: {tabla_origen}")
        ingestion_time = datetime.now()

        column_hints = get_column_hints(engine, tabla_origen)
        with engine.connect() as conn:
            filas = fetch_filas_incremental(conn, tabla_origen, CAMPO_CURSOR_MEDICARE_ORIGEN, watermark, ingestion_time)

        if filas:
            run_pipeline_seguro(pipeline, filas, table_name=tabla_landing, write_disposition="append", columns=column_hints)
            print(f"   [MEDICARE] OK: {len(filas)} filas nuevas cargadas en {tabla_origen}.")
        else:
            print(f"   [MEDICARE] OK: Sin cambios en {tabla_origen}.")

    engine.dispose()
    sf_conn.close()
    fin = datetime.now()
    print(f"\n[MEDICARE] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')} | Duracion total: {fin - inicio}\n{'='*60}")


# ---------------------------------------------------------------
# FUENTE 2: NEXTBIO (PostgreSQL)
# ---------------------------------------------------------------
def load_nextbio_landing() -> None:
    inicio = datetime.now()
    print(f"\n{'='*60}\n[NEXTBIO] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")

    pipeline = dlt.pipeline(
        pipeline_name="nextbio_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_NEXTBIO,
        pipelines_dir=r"C:\dlt_temp\nextbio"
    )

    sf_conn = get_snowflake_connection()
    engine = sa.create_engine(dlt.secrets["conexion_nextbio"])
    print("\n[NEXTBIO] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in TABLAS_NEXTBIO.items():
        watermark = get_watermark(sf_conn, SCHEMA_LANDING_NEXTBIO, tabla_landing, CAMPO_CURSOR_NEXTBIO)
        print(f"  [NEXTBIO] -> Tabla: {tabla_origen}")
        ingestion_time = datetime.now()

        column_hints = get_column_hints(engine, tabla_origen)
        with engine.connect() as conn:
            filas = fetch_filas_incremental(conn, tabla_origen, CAMPO_CURSOR_NEXTBIO, watermark, ingestion_time)

        if filas:
            run_pipeline_seguro(pipeline, filas, table_name=tabla_landing, write_disposition="append", columns=column_hints)
            print(f"  [NEXTBIO]   OK: {len(filas)} filas nuevas cargadas en {tabla_origen}.")
        else:
            print(f"  [NEXTBIO]   OK: Sin cambios en {tabla_origen}.")

    engine.dispose()
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
        cursor.execute(f"SELECT DISTINCT FICHERO_ORIGEN FROM {SCHEMA_LANDING_PRODUCTOS}.{TABLA_PRODUCTOS}")
        ficheros_procesados = {row[0] for row in cursor.fetchall()}
    except Exception:
        ficheros_procesados = set()
    finally:
        cursor.close()

    blob_service = BlobServiceClient(
        account_url=f"https://{dlt.secrets['azure_storage_account_name']}.blob.core.windows.net",
        credential=dlt.secrets['azure_storage_sas_token']
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

        ingestion_time = datetime.now()
        datos = []
        for fila in reader:
            fila["FICHERO_ORIGEN"] = fichero
            fila["fecha_ingestion"] = ingestion_time
            datos.append(dict(fila))

        run_pipeline_seguro(pipeline, datos, table_name=TABLA_PRODUCTOS, write_disposition="append")
        print(f"  [PRODUCTOS CSV]   OK: {len(datos)} filas cargadas del fichero {fichero}.")

    sf_conn.close()
    fin = datetime.now()
    print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')} | Duracion total: {fin - inicio}\n{'='*60}")


# Helper para reintentos automáticos en caso de que me bloquee los archivos el Windows Defender
def run_pipeline_seguro(pipeline, data, **kwargs):
    import time
    for intento in range(3):
        try:
            return pipeline.run(data, **kwargs)
        except Exception as e:
            error_str = str(e)
            if ("WinError 5" in error_str or "WinError 145" in error_str) and intento < 2:
                print(f"     [!] Windows bloqueó archivo. Reintento {intento+1}/3...")
                time.sleep(5)
            elif "already completed" in error_str.lower():
                return
            elif "stage" in error_str.lower() and "does not exist" in error_str.lower() and intento < 2:
                print(f"     [!] Stage de Snowflake no disponible aún. Reintento {intento+1}/3...")
                time.sleep(10)
            else:
                raise


# ---------------------------------------------------------------
# MAIN (Botón de arranque para el orquestador main.py) engloba las 3 fuentes en paralelo 
# ---------------------------------------------------------------
def ejecutar_extraccion_completa():
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
