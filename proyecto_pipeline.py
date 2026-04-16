# ---------------------------------------------------------------
# proyecto_pipeline.py
# Pipeline de ingesta incremental hacia Snowflake (capa LANDING)
# Fuentes: MEDICARE (SQL Server), NEXTBIO (PostgreSQL), CSV (Azure Blob)
# ---------------------------------------------------------------

import os
import tempfile
import dlt
from dlt.sources.sql_database import sql_table
import sqlalchemy as sa
import logging
# logging.getLogger("dlt").setLevel(logging.ERROR)  # descomentar para silenciar logs de dlt
from concurrent.futures import ThreadPoolExecutor, as_completed # para ejecutar las cargas en paralelo y ahorrar tiempo 

from datos import (
    SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_ROLE,
    TABLAS_MEDICARE, SCHEMA_LANDING_MEDICARE, CAMPO_CURSOR_MEDICARE_SNOWFLAKE,CAMPO_CURSOR_MEDICARE_ORIGEN,
    TABLAS_NEXTBIO, SCHEMA_LANDING_NEXTBIO, CAMPO_CURSOR_NEXTBIO,
    SCHEMA_LANDING_PRODUCTOS, TABLA_PRODUCTOS,
    AZURE_ACCOUNT_NAME, AZURE_CONTAINER_NAME, AZURE_SAS_TOKEN,
)


def get_snowflake_connection():
    """Devuelve una conexión a Snowflake usando las credenciales de config.py"""
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
    """Obtiene el watermark (MAX fecha) de una tabla en Snowflake."""
    from datetime import datetime
    cursor = sf_conn.cursor()
    try:
        cursor.execute(f"SELECT COALESCE(MAX({campo_cursor}), '1900-01-01'::TIMESTAMP) FROM {SNOWFLAKE_DATABASE}.{schema}.{tabla_landing.upper()}")
        result = cursor.fetchone()[0]
        if isinstance(result, str):
            return datetime.strptime(result[:19], '%Y-%m-%d %H:%M:%S')
        return result if result else datetime(1900, 1, 1)
    except Exception:
        from datetime import datetime
        return datetime(1900, 1, 1)
    finally:
        cursor.close()


# ---------------------------------------------------------------
# FUENTE 1: MEDICARE (Azure SQL Server)
# ---------------------------------------------------------------
# def load_medicare_landing() -> None:
#     from datetime import datetime
#     inicio = datetime.now()
#     print(f"\n{'='*60}")
#     print(f"[MEDICARE] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"{'='*60}")

#     sf_conn = get_snowflake_connection()
#     #directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_medicare_limpio")
#     directorio_seguro = r"C:\dlt_temp\medicare"  # ruta fija para evitar problemas de permisos en algunos sistemas operativos (ej: Windows) con tempfile

#     pipeline = dlt.pipeline(
#         pipeline_name="medicare_to_landing",
#         destination="snowflake",
#         dataset_name=SCHEMA_LANDING_MEDICARE,
#         pipelines_dir=directorio_seguro
#     )

#     print("\n[MEDICARE] Conectando a la base de datos origen...")

#     for tabla_origen, tabla_landing in TABLAS_MEDICARE.items():
#         watermark = get_watermark(sf_conn, SCHEMA_LANDING_MEDICARE, tabla_landing, CAMPO_CURSOR_MEDICARE_SNOWFLAKE)
#         print(f"  -> Tabla: {tabla_origen} | Watermark: {watermark}")

#         resource = sql_table(
#             credentials=dlt.secrets["conexion_medicare"],
#             table=tabla_origen,
#             incremental=dlt.sources.incremental(
#                 CAMPO_CURSOR_MEDICARE_ORIGEN,
#                 initial_value=watermark,
#                 last_value_func=max
#             )
#         )

#         info = pipeline.run([resource], write_disposition="append")
#         filas_cargadas = sum(info.row_counts.values()) if hasattr(info, 'row_counts') and info.row_counts else 0

#         if filas_cargadas > 0:
#             print(f"     Se han cargado {filas_cargadas} filas nuevas...")
#         else:
#             print(f"     No hay cambios.")
#         print(f"     OK: {tabla_origen} procesada.")

#     sf_conn.close()
#     fin = datetime.now()
#     print(f"\n[MEDICARE] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"[MEDICARE] Duracion total: {fin - inicio}")
#     print(f"{'='*60}")





def load_medicare_landing() -> None:
    from datetime import datetime
    import time  # <-- Importante para la pausa del reintento
    
    inicio = datetime.now()
    print(f"\n{'='*60}")
    print(f"[MEDICARE] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    sf_conn = get_snowflake_connection()
    #directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_medicare_limpio")
    directorio_seguro = r"C:\dlt_temp\medicare"  # ruta fija para evitar problemas de permisos en algunos sistemas operativos (ej: Windows) con tempfile

    pipeline = dlt.pipeline(
        pipeline_name="medicare_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_MEDICARE,
        pipelines_dir=directorio_seguro
    )

    print("\n[MEDICARE] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in TABLAS_MEDICARE.items():
        watermark = get_watermark(sf_conn, SCHEMA_LANDING_MEDICARE, tabla_landing, CAMPO_CURSOR_MEDICARE_SNOWFLAKE)
        print(f"  -> Tabla: {tabla_origen} | Watermark: {watermark}")

        resource = sql_table(
            credentials=dlt.secrets["conexion_medicare"],
            table=tabla_origen,
            incremental=dlt.sources.incremental(
                CAMPO_CURSOR_MEDICARE_ORIGEN,
                initial_value=watermark,
                last_value_func=max
            )
        )

        # --- LÓGICA DE REINTENTO A PRUEBA DE FALLOS (WINERROR 5) ---
        max_reintentos = 3
        
        for intento in range(max_reintentos):
            try:
                # Intentamos ejecutar la carga
                info = pipeline.run([resource], write_disposition="append")
                break  # Si funciona a la primera, rompemos el bucle y seguimos
            
            except PermissionError as e:  # Si Windows bloquea el archivo (WinError 5)
                if intento < max_reintentos - 1:
                    print(f"     [!] Windows bloqueó un archivo temporal. Reintentando en 5s... (Intento {intento+1}/{max_reintentos})")
                    time.sleep(5)  # Damos 5 segundos a Windows para que libere el archivo
                else:
                    print(f"     [ERROR FATAL] No se pudo procesar {tabla_origen} tras {max_reintentos} intentos.")
                    raise e  # Si falla 3 veces seguidas, entonces sí abortamos
        # ------------------------------------------------------------

        # --- NUEVA LÓGICA DE PRINTS (CORREGIDA) ---
# --- NUEVA LÓGICA DE PRINTS (EXACTA) ---
        try:
            conteos = pipeline.last_trace.last_normalize_info.row_counts
            # Sumamos las filas solo de las tablas reales (ignoramos las que empiezan por "_dlt")
            filas_cargadas = sum(filas for tabla, filas in conteos.items() if not tabla.startswith("_dlt"))
        except (AttributeError, TypeError):
            filas_cargadas = 0

        if filas_cargadas > 0:
            print(f"     Se han cargado {filas_cargadas} filas nuevas...")
        else:
            print(f"     No hay cambios.")
        # ---------------------------------------

    sf_conn.close()
    fin = datetime.now()
    print(f"\n[MEDICARE] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[MEDICARE] Duracion total: {fin - inicio}")
    print(f"{'='*60}")

# ---------------------------------------------------------------
# FUENTE 2: NEXTBIO (PostgreSQL)
# ---------------------------------------------------------------
# def load_nextbio_landing() -> None:
#     from datetime import datetime
#     import pandas as pd
#     inicio = datetime.now()
#     print(f"\n{'='*60}")
#     print(f"[NEXTBIO] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"{'='*60}")

#     sf_conn = get_snowflake_connection()
#     #directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_nextbio_limpio")
#     directorio_seguro = r"C:\dlt_temp\nextbio"  # ruta fija para evitar problemas de permisos en algunos sistemas operativos (ej: Windows) con tempfile

#     pipeline = dlt.pipeline(
#         pipeline_name="nextbio_to_landing",
#         destination="snowflake",
#         dataset_name=SCHEMA_LANDING_NEXTBIO,
#         pipelines_dir=directorio_seguro
#     )

#     print("\n[NEXTBIO] Conectando a la base de datos origen...")

#     for tabla_origen, tabla_landing in TABLAS_NEXTBIO.items():
#         watermark = get_watermark(sf_conn, SCHEMA_LANDING_NEXTBIO, tabla_landing, CAMPO_CURSOR_NEXTBIO)
#         print(f"  -> Tabla: {tabla_origen} | Watermark: {watermark}")

#         # lecturas_signos_vitales tiene 876.830 registros con la misma fecha_modificacion
#         # dlt no puede guardar el estado de deduplicacion (supera 16MB en Snowflake)
#         # Solución: cargamos con pandas directamente sin incremental de dlt
#         if tabla_origen == "lecturas_signos_vitales":
#             engine = sa.create_engine(dlt.secrets["conexion_nextbio"])
#             query = f"SELECT * FROM lecturas_signos_vitales WHERE {CAMPO_CURSOR_NEXTBIO} > '{watermark}'"
#             df = pd.read_sql(query, engine)
#             engine.dispose()

#             if len(df) > 0:
#                 print(f"     Se han cargado {len(df)} filas nuevas...")
#                 pipeline_lecturas = dlt.pipeline(
#                     pipeline_name="nextbio_lecturas_to_landing",
#                     destination="snowflake",
#                     dataset_name=SCHEMA_LANDING_NEXTBIO,
#                     pipelines_dir=directorio_seguro,
#                 )
#                 pipeline_lecturas.run(
#                     df.to_dict(orient="records"),
#                     table_name="lecturas_signos_vitales",
#                     write_disposition="append"
#                 )
#             else:
#                 print(f"     No hay cambios.")
#         else:
#             resource = sql_table(
#                 credentials=dlt.secrets["conexion_nextbio"],
#                 table=tabla_origen,
#                 incremental=dlt.sources.incremental(
#                     CAMPO_CURSOR_NEXTBIO,
#                     initial_value=watermark,
#                     last_value_func=max
#                 )
#             )
#             info = pipeline.run([resource], write_disposition="append")
#             filas_cargadas = sum(info.row_counts.values()) if hasattr(info, 'row_counts') and info.row_counts else 0

#             if filas_cargadas > 0:
#                 print(f"     Se han cargado {filas_cargadas} filas nuevas...")
#             else:
#                 print(f"     No hay cambios.")

#         print(f"     OK: {tabla_origen} procesada.")

#     sf_conn.close()
#     fin = datetime.now()
#     print(f"\n[NEXTBIO] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"[NEXTBIO] Duracion total: {fin - inicio}")
#     print(f"{'='*60}")

def load_nextbio_landing() -> None:
    from datetime import datetime
    import pandas as pd
    import time  # <-- Necesario para el sleep de los reintentos
    
    inicio = datetime.now()
    print(f"\n{'='*60}")
    print(f"[NEXTBIO] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    sf_conn = get_snowflake_connection()
    #directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_nextbio_limpio")
    directorio_seguro = r"C:\dlt_temp\nextbio"  # ruta fija para evitar problemas de permisos en algunos sistemas operativos (ej: Windows) con tempfile

    pipeline = dlt.pipeline(
        pipeline_name="nextbio_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_NEXTBIO,
        pipelines_dir=directorio_seguro
    )

    print("\n[NEXTBIO] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in TABLAS_NEXTBIO.items():
        watermark = get_watermark(sf_conn, SCHEMA_LANDING_NEXTBIO, tabla_landing, CAMPO_CURSOR_NEXTBIO)
        print(f"  -> Tabla: {tabla_origen} | Watermark: {watermark}")

        # lecturas_signos_vitales tiene 876.830 registros con la misma fecha_modificacion
        # dlt no puede guardar el estado de deduplicacion (supera 16MB en Snowflake)
        # Solución: cargamos con pandas directamente sin incremental de dlt
        if tabla_origen == "lecturas_signos_vitales":
            engine = sa.create_engine(dlt.secrets["conexion_nextbio"])
            query = f"SELECT * FROM lecturas_signos_vitales WHERE {CAMPO_CURSOR_NEXTBIO} > '{watermark}'"
            df = pd.read_sql(query, engine)
            engine.dispose()

            if len(df) > 0:
                print(f"     Se han cargado {len(df)} filas nuevas...")
                pipeline_lecturas = dlt.pipeline(
                    pipeline_name="nextbio_lecturas_to_landing",
                    destination="snowflake",
                    dataset_name=SCHEMA_LANDING_NEXTBIO,
                    pipelines_dir=directorio_seguro,
                )
                
                # --- LÓGICA DE REINTENTO PARA PANDAS ---
                max_reintentos = 3
                for intento in range(max_reintentos):
                    try:
                        pipeline_lecturas.run(
                            df.to_dict(orient="records"),
                            table_name="lecturas_signos_vitales",
                            write_disposition="append"
                        )
                        break
                    except PermissionError as e:
                        if intento < max_reintentos - 1:
                            print(f"     [!] Windows bloqueó un archivo temporal. Reintentando en 5s... (Intento {intento+1}/{max_reintentos})")
                            time.sleep(5)
                        else:
                            print(f"     [ERROR FATAL] No se pudo procesar {tabla_origen} tras {max_reintentos} intentos.")
                            raise e
                # ---------------------------------------
            else:
                print(f"     No hay cambios.")
                
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
            
            # --- LÓGICA DE REINTENTO PARA DLT NORMAL ---
            max_reintentos = 3
            for intento in range(max_reintentos):
                try:
                    pipeline.run([resource], write_disposition="append")
                    break
                except PermissionError as e:
                    if intento < max_reintentos - 1:
                        print(f"     [!] Windows bloqueó un archivo temporal. Reintentando en 5s... (Intento {intento+1}/{max_reintentos})")
                        time.sleep(5)
                    else:
                        print(f"     [ERROR FATAL] No se pudo procesar {tabla_origen} tras {max_reintentos} intentos.")
                        raise e
            # -------------------------------------------

            # --- NUEVA LÓGICA DE PRINTS (EXACTA) ---
            try:
                conteos = pipeline.last_trace.last_normalize_info.row_counts
                # Sumamos las filas solo de las tablas reales (ignoramos las que empiezan por "_dlt")
                filas_cargadas = sum(filas for tabla, filas in conteos.items() if not tabla.startswith("_dlt"))
            except (AttributeError, TypeError):
                filas_cargadas = 0

            if filas_cargadas > 0:
                print(f"     Se han cargado {filas_cargadas} filas nuevas...")
            else:
                print(f"     No hay cambios.")
            # ---------------------------------------

        print(f"     OK: {tabla_origen} procesada.")

    sf_conn.close()
    fin = datetime.now()
    print(f"\n[NEXTBIO] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[NEXTBIO] Duracion total: {fin - inicio}")
    print(f"{'='*60}")


# # ---------------------------------------------------------------
# # FUENTE 3: CSV PRODUCTOS SANITARIOS (Azure Blob Storage)
# # ---------------------------------------------------------------
# def load_productos_landing() -> None:
#     from datetime import datetime
#     import pandas as pd
#     import io
#     from azure.storage.blob import BlobServiceClient

#     inicio = datetime.now()
#     print(f"\n{'='*60}")
#     print(f"[PRODUCTOS CSV] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"{'='*60}")

#     sf_conn = get_snowflake_connection()
#     cursor = sf_conn.cursor()
#     try:
#         cursor.execute(f"SELECT DISTINCT FICHERO_ORIGEN FROM {SNOWFLAKE_DATABASE}.{SCHEMA_LANDING_PRODUCTOS}.{TABLA_PRODUCTOS}")
#         ficheros_procesados = {row[0] for row in cursor.fetchall()}
#     except Exception:
#         ficheros_procesados = set()
#     finally:
#         cursor.close()

#     print(f"\n[PRODUCTOS CSV] Ficheros ya procesados en Snowflake: {len(ficheros_procesados)}")
#     for f in sorted(ficheros_procesados):
#         print(f"     - {f}")

#     blob_service = BlobServiceClient(
#         account_url=f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net",
#         credential=AZURE_SAS_TOKEN
#     )
#     container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)
#     blobs = [b.name for b in container_client.list_blobs() if b.name.endswith(".csv")]

#     print(f"\n[PRODUCTOS CSV] Ficheros disponibles en Azure Blob Storage: {len(blobs)}")
#     for b in sorted(blobs):
#         print(f"     - {b}")

#     ficheros_nuevos = [b for b in blobs if b not in ficheros_procesados]
#     print(f"\n[PRODUCTOS CSV] Ficheros nuevos a procesar: {len(ficheros_nuevos)}")

#     if not ficheros_nuevos:
#         print("     No hay ficheros nuevos que procesar.")
#         sf_conn.close()
#         fin = datetime.now()
#         print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
#         print(f"[PRODUCTOS CSV] Duracion total: {fin - inicio}")
#         print(f"{'='*60}")
#         return

#     #directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_productos_limpio")
#     directorio_seguro = r"C:\dlt_temp\productos"
#     pipeline = dlt.pipeline(
#         pipeline_name="productos_to_landing",
#         destination="snowflake",
#         dataset_name=SCHEMA_LANDING_PRODUCTOS,
#         pipelines_dir=directorio_seguro
#     )

#     for fichero in ficheros_nuevos:
#         print(f"\n  -> Procesando: {fichero}")
#         blob_client = blob_service.get_blob_client(container=AZURE_CONTAINER_NAME, blob=fichero)
#         content = blob_client.download_blob().readall().decode("utf-8")
#         df = pd.read_csv(io.StringIO(content), sep=";")
#         df["FICHERO_ORIGEN"] = fichero

#         info = pipeline.run(
#             df.to_dict(orient="records"),
#             table_name=TABLA_PRODUCTOS,
#             write_disposition="append"
#         )
#         filas = sum(info.row_counts.values()) if hasattr(info, 'row_counts') and info.row_counts else len(df)
#         print(f"     OK: {filas} filas cargadas.")

#     sf_conn.close()
#     fin = datetime.now()
#     print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"[PRODUCTOS CSV] Duracion total: {fin - inicio}")
#     print(f"{'='*60}")


def load_productos_landing() -> None:
    from datetime import datetime
    import csv  # <-- Sustituimos pandas por el módulo nativo csv
    import io
    import time
    from azure.storage.blob import BlobServiceClient

    inicio = datetime.now()
    print(f"\n{'='*60}")
    print(f"[PRODUCTOS CSV] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    sf_conn = get_snowflake_connection()
    cursor = sf_conn.cursor()
    try:
        cursor.execute(f"SELECT DISTINCT FICHERO_ORIGEN FROM {SNOWFLAKE_DATABASE}.{SCHEMA_LANDING_PRODUCTOS}.{TABLA_PRODUCTOS}")
        ficheros_procesados = {row[0] for row in cursor.fetchall()}
    except Exception:
        ficheros_procesados = set()
    finally:
        cursor.close()

    print(f"\n[PRODUCTOS CSV] Ficheros ya procesados en Snowflake: {len(ficheros_procesados)}")
    for f in sorted(ficheros_procesados):
        print(f"     - {f}")

    blob_service = BlobServiceClient(
        account_url=f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=AZURE_SAS_TOKEN
    )
    container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)
    blobs = [b.name for b in container_client.list_blobs() if b.name.endswith(".csv")]

    print(f"\n[PRODUCTOS CSV] Ficheros disponibles en Azure Blob Storage: {len(blobs)}")
    for b in sorted(blobs):
        print(f"     - {b}")

    ficheros_nuevos = [b for b in blobs if b not in ficheros_procesados]
    print(f"\n[PRODUCTOS CSV] Ficheros nuevos a procesar: {len(ficheros_nuevos)}")

    if not ficheros_nuevos:
        print("     No hay ficheros nuevos que procesar.")
        sf_conn.close()
        fin = datetime.now()
        print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[PRODUCTOS CSV] Duracion total: {fin - inicio}")
        print(f"{'='*60}")
        return

    directorio_seguro = r"C:\dlt_temp\productos"
    pipeline = dlt.pipeline(
        pipeline_name="productos_to_landing",
        destination="snowflake",
        dataset_name=SCHEMA_LANDING_PRODUCTOS,
        pipelines_dir=directorio_seguro
    )

    for fichero in ficheros_nuevos:
        print(f"\n  -> Procesando: {fichero}")
        blob_client = blob_service.get_blob_client(container=AZURE_CONTAINER_NAME, blob=fichero)
        
        # 1. Descargamos y decodificamos el contenido
        content = blob_client.download_blob().readall().decode("utf-8")
        
        # 2. PROCESAMIENTO NATIVO (Sustituye a Pandas)
        # Usamos DictReader para convertir cada fila en un diccionario automáticamente
        fichero_csv = io.StringIO(content)
        reader = csv.DictReader(fichero_csv, delimiter=";")
        
        datos = []
        for fila in reader:
            fila["FICHERO_ORIGEN"] = fichero  # Añadimos la columna de trazabilidad
            datos.append(dict(fila))

        # --- LÓGICA DE REINTENTO (WINERROR 5) ---
        max_reintentos = 3
        for intento in range(max_reintentos):
            try:
                # dlt acepta la lista de diccionarios directamente
                pipeline.run(
                    datos,
                    table_name=TABLA_PRODUCTOS,
                    write_disposition="append"
                )
                break
            except PermissionError as e:
                if intento < max_reintentos - 1:
                    print(f"     [!] Windows bloqueó un archivo temporal. Reintentando en 5s... (Intento {intento+1}/{max_reintentos})")
                    time.sleep(5)
                else:
                    print(f"     [ERROR FATAL] No se pudo procesar el fichero {fichero} tras {max_reintentos} intentos.")
                    raise e
        # ----------------------------------------

        # --- LÓGICA DE PRINTS (EXACTA) ---
        try:
            conteos = pipeline.last_trace.last_normalize_info.row_counts
            filas_cargadas = sum(filas for tabla, filas in conteos.items() if not tabla.startswith("_dlt"))
        except (AttributeError, TypeError):
            # Si falla la traza, usamos el tamaño de nuestra lista de datos
            filas_cargadas = len(datos)

        print(f"     OK: Se han cargado {filas_cargadas} filas nuevas.")

    sf_conn.close()
    fin = datetime.now()
    print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[PRODUCTOS CSV] Duracion total: {fin - inicio}")
    print(f"{'='*60}")


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------

#ejecucion en paralelo con ThreadPoolExecutor con un retardo de 2 segundos. 
#comparte el mismo espacio de memoria, por lo que es más ligero pero puede haber colisiones si las funciones no están bien diseñadas (en este caso no hay problemas porque cada función trabaja con recursos independientes)

if __name__ == '__main__':
    import time
    funciones = [
        load_medicare_landing,
        #load_nextbio_landing,
        load_productos_landing
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for f in funciones:
            futures[executor.submit(f)] = f.__name__
            time.sleep(2)  # pequeño retraso entre lanzamientos por si salta algun fallo al iniciar varias conexiones a la vez (opcional, se puede comentar)
        for future in as_completed(futures):
            nombre = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[ERROR] {nombre} falló: {e}")



#ejecucion en paralelo con ProcessPoolExecutor para ahorrar tiempo (carga de las 3 fuentes al mismo tiempo)
# cada proceso tiene su propio espacio de memoria y sistema de ficheros, evitando las colisiones

# if __name__ == '__main__':
#     from concurrent.futures import ProcessPoolExecutor, as_completed

#     funciones = [
#         load_medicare_landing,
#         load_nextbio_landing,
#         load_productos_landing
#     ]

#     with ProcessPoolExecutor(max_workers=3) as executor:
#         futures = {executor.submit(f): f.__name__ for f in funciones}
#         for future in as_completed(futures):
#             nombre = futures[future]
#             try:
#                 future.result()
#             except Exception as e:
#                 print(f"[ERROR] {nombre} falló: {e}")





# ejecucion secuencial sin paralelismo
# if __name__ == '__main__':
#     load_medicare_landing()
#     load_nextbio_landing()
#     load_productos_landing()



#para limpiar los estado de DLT con rutas dinámicas (tempfile):
#Remove-Item -Recurse -Force "$env:TEMP\dlt_medicare_limpio"
#Remove-Item -Recurse -Force "$env:TEMP\dlt_nextbio_limpio"
#Remove-Item -Recurse -Force "$env:TEMP\dlt_productos_limpio"





#AHORA ESTOY USANDO ESTAS RUTAS ACTUALMENTE PARA EVITAR PROBLEMAS DE PERMISOS CON TEMPFILE EN WINDOWS (WINERROR 5):
#para limpiar los estado de DLT con rutas fijas (Windows):
#Remove-Item -Recurse -Force C:\dlt_temp\medicare
#Remove-Item -Recurse -Force C:\dlt_temp\nextbio
#Remove-Item -Recurse -Force C:\dlt_temp\productos



