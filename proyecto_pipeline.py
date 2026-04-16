

# ---------------------------------------------------------------
# Pipeline de ingesta incremental hacia Snowflake (capa LANDING)
# Fuentes: MEDICARE (SQL Server), NEXTBIO (PostgreSQL), CSV (Azure Blob)
# ---------------------------------------------------------------

import os
import dlt
from dlt.sources.sql_database import sql_table
import sqlalchemy as sa
import logging
# logging.getLogger("dlt").setLevel(logging.ERROR)  # descomentar para silenciar logs de dlt





# ---------------------------------------------------------------
# -------------------------------------------FUENTE 1: MEDICARE (Azure SQL Server)-------------------------------------------------------------------------------------------------
# ================================================================
# INGESTA INCREMENTAL HACIA PROYECTO.LANDING (CAPA BRONCE)
# 


def load_medicare_landing() -> None:
    from datetime import datetime
    import snowflake.connector
    import dlt
    from dlt.sources.sql_database import sql_table
    import os
    import tempfile

    inicio = datetime.now()
    print(f"\n{'='*60}")
    print(f"[MEDICARE] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Conectar a Snowflake para obtener el watermark
    sf_conn = snowflake.connector.connect(
        user="JORGEMS96",
        password="dJuniversidad.1",
        account="jrtuvgy-tq97242",
        warehouse="COMPUTE_WH",
        database="PROYECTO",
        role="ACCOUNTADMIN"
    )

    tablas = {
        "CategoriaEquipos":         "categoria_equipos",
        "ConsumoRepuestos":         "consumo_repuestos",
        "Departamentos":            "departamentos",
        "Equipos":                  "equipos",
        "Fabricantes":              "fabricantes",
        "PlanificacionPreventivos": "planificacion_preventivos",
        "Repuestos":                "repuestos",
        "Tecnicos":                 "tecnicos",
        "Ubicaciones":              "ubicaciones",
        "OrdenesMantenimiento":     "ordenes_mantenimiento",
    }

    directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_medicare_limpio")

    pipeline = dlt.pipeline(
        pipeline_name="medicare_to_landing",
        destination="snowflake",
        dataset_name="LANDING_MEDICARE",
        pipelines_dir=directorio_seguro
    )

    print("\n[MEDICARE] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in tablas.items():
        # 1. Obtenemos el watermark de Snowflake
        cursor = sf_conn.cursor()
        try:
            cursor.execute(f"SELECT COALESCE(MAX(FECHA_MODIFICACION), '1900-01-01'::TIMESTAMP) FROM PROYECTO.LANDING_MEDICARE.{tabla_landing.upper()}")
            result = cursor.fetchone()[0]
            
            # print(f"     DEBUG watermark result: {result} | type: {type(result)}")
            
            # Convertir a datetime si es string
            if isinstance(result, str):
                watermark = datetime.strptime(result[:19], '%Y-%m-%d %H:%M:%S')
            else:
                watermark = result if result else datetime(1900, 1, 1)
        except Exception as e:
            # print(f"     DEBUG watermark error: {e}")
            watermark = datetime(1900, 1, 1)
        cursor.close()

        print(f"  -> Tabla: {tabla_origen} | Watermark: {watermark}")

        # 2. Configuramos la carga incremental
        resource = sql_table(
            credentials=dlt.secrets["conexion_medicare"], #COMENTARLA SI NO FUNCIONA
            table=tabla_origen,
            incremental=dlt.sources.incremental(
                "FechaModificacion",
                initial_value=watermark,
                last_value_func=max
            )
        )

        # 3. Ejecutamos
        info = pipeline.run([resource], write_disposition="append")
        
        # --- NUEVA LÓGICA DE PRINTS PARA DLT ---
        # Extraemos la cantidad de filas del objeto "info"
        filas_cargadas = sum(info.row_counts.values()) if hasattr(info, 'row_counts') and info.row_counts else 0
        
        if filas_cargadas > 0:
            print(f"     Se han cargado {filas_cargadas} filas nuevas...")
        else:
            print(f"     No hay cambios.")
        # ---------------------------------------
        
        print(f"     OK: {tabla_origen} procesada.")

    sf_conn.close()
    fin = datetime.now()
    duracion = fin - inicio
    print(f"\n[MEDICARE] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[MEDICARE] Duracion total: {duracion}")
    print(f"{'='*60}")



# ===============================================================
# ---------------------------------------------------------------
# -------------------------------------------------FUENTE 2: NEXTBIO (POSTGRESQL)---------------------------------------------------------------------------------------------------------------------------
# INGESTA INCREMENTAL HACIA PROYECTO.LANDING (CAPA BRONCE)

def load_nextbio_landing() -> None:
    from datetime import datetime
    import snowflake.connector
    import dlt
    from dlt.sources.sql_database import sql_table
    import os
    import tempfile
    import sqlalchemy as sa
    import pandas as pd

    inicio = datetime.now()
    print(f"\n{'='*60}")
    print(f"[NEXTBIO] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Conectar a Snowflake para obtener el watermark
    sf_conn = snowflake.connector.connect(
        user="JORGEMS96",
        password="dJuniversidad.1",
        account="jrtuvgy-tq97242",
        warehouse="COMPUTE_WH",
        database="PROYECTO",
        role="ACCOUNTADMIN"
    )

    tablas = {
        "diagnosticos_cie10":      "diagnosticos_cie10",
        "ensayos_clinicos":        "ensayos_clinicos",
        "especialidades":          "especialidades",
        "lecturas_signos_vitales": "lecturas_signos_vitales",
        "medicos":                 "medicos",
        "monitorizaciones":        "monitorizaciones",
        "paciente_diagnostico":    "paciente_diagnostico",
        "pacientes":               "pacientes",
        "participacion_ensayos":   "participacion_ensayos",
        "visitas_ensayo":          "visitas_ensayo",
    }

    directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_nextbio_limpio")

    pipeline = dlt.pipeline(
        pipeline_name="nextbio_to_landing",
        destination="snowflake",
        dataset_name="LANDING_NEXTBIO",
        pipelines_dir=directorio_seguro
    )

    print("\n[NEXTBIO] Conectando a la base de datos origen...")

    for tabla_origen, tabla_landing in tablas.items():
        # 1. Obtenemos el watermark de Snowflake
        cursor = sf_conn.cursor()
        try:
            cursor.execute(f"SELECT COALESCE(MAX(FECHA_MODIFICACION), '1900-01-01'::TIMESTAMP) FROM PROYECTO.LANDING_NEXTBIO.{tabla_landing.upper()}")
            result = cursor.fetchone()[0]
            if isinstance(result, str):
                watermark = datetime.strptime(result[:19], '%Y-%m-%d %H:%M:%S')
            else:
                watermark = result if result else datetime(1900, 1, 1)
        except Exception as e:
            watermark = datetime(1900, 1, 1)
        cursor.close()

        print(f"  -> Tabla: {tabla_origen} | Watermark: {watermark}")

        # 2. Configuramos la carga incremental, pero con una excepción para la tabla "lecturas_signos_vitales" que tiene demasiados registros con la misma fecha_modificacion   
        if tabla_origen == "lecturas_signos_vitales":
            # Esta tabla tiene 50000+ registros con la misma fecha_modificacion
            # dlt no puede guardar el estado de deduplicacion (supera 16MB en Snowflake)
            # Solución: cargamos con pandas directamente sin incremental de dlt
            string_conexion = dlt.secrets["conexion_nextbio"]
            engine = sa.create_engine(string_conexion)
            #"postgresql+psycopg2://sgc_readonly:SgcReadOnly2026!@dxc-bootcamp-fy27-postgres.postgres.database.azure.com:5432/NEXTBIO"
            
            query = f"SELECT * FROM lecturas_signos_vitales WHERE fecha_modificacion > '{watermark}'"
            df = pd.read_sql(query, engine)
            engine.dispose()

            if len(df) > 0:
                print(f"     Se han cargado {len(df)} filas nuevas...")
                pipeline_lecturas = dlt.pipeline(
                    pipeline_name="nextbio_lecturas_to_landing",
                    destination="snowflake",
                    dataset_name="LANDING_NEXTBIO",
                    pipelines_dir=directorio_seguro,
                )
                info = pipeline_lecturas.run(
                    df.to_dict(orient="records"),
                    table_name="lecturas_signos_vitales",
                    write_disposition="append"
                )
            else:
                print(f"     No hay cambios.")
        #pero si es otra tabla, cargamos con dlt normalmente usando incremental
        else:
            resource = sql_table(
                credentials=dlt.secrets["conexion_nextbio"], #COMENTARLA SI NO FUNCIONA
                table=tabla_origen,
                incremental=dlt.sources.incremental(
                    "fecha_modificacion",
                    initial_value=watermark,
                    last_value_func=max
                )
            )
            info = pipeline.run([resource], write_disposition="append")
            
            # --- NUEVA LÓGICA DE PRINTS PARA DLT ---
            # Extraemos la cantidad de filas del objeto "info"
            filas_cargadas = sum(info.row_counts.values()) if hasattr(info, 'row_counts') and info.row_counts else 0
            
            if filas_cargadas > 0:
                print(f"     Se han cargado {filas_cargadas} filas nuevas...")
            else:
                print(f"     No hay cambios.")
            # ---------------------------------------

        print(f"     OK: {tabla_origen} procesada.")

    sf_conn.close()
    fin = datetime.now()
    duracion = fin - inicio
    print(f"\n[NEXTBIO] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[NEXTBIO] Duracion total: {duracion}")
    print(f"{'='*60}")


# ---------------------------------------------------------------
# FUENTE 3: CSV PRODUCTOS SANITARIOS (Azure Blob Storage)
# Activar en secrets.toml:
#   [sources.filesystem.credentials]
#   azure_storage_account_name = "sascvbootcamp"
#   azure_storage_sas_token = "sp=rl&st=2026-04-07T10:43:32Z&se=2026-06-30T18:58:32Z&sv=2025-11-05&sr=c&sig=2dhrhfePaVhLt0CEHAlogDUXteDSbdZDc1VM6xefJHI%3D"
# ---------------------------------------------------------------



def load_productos_landing() -> None:
    """Ingesta incremental de CSV de Productos Sanitarios hacia PROYECTO.LANDING_PRODUCTOS.
    - Consulta en Snowflake qué ficheros ya han sido procesados (FICHERO_ORIGEN).
    - Solo descarga y procesa los ficheros nuevos del Blob Storage.
    - Añade columna FICHERO_ORIGEN con el nombre del CSV de origen.
    """
    from datetime import datetime
    import snowflake.connector
    import dlt
    import os
    import tempfile
    import pandas as pd
    import io
    from azure.storage.blob import BlobServiceClient
 
    inicio = datetime.now()
    print(f"\n{'='*60}")
    print(f"[PRODUCTOS CSV] Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
 
    # 1. Conectar a Snowflake y obtener ficheros ya procesados
    sf_conn = snowflake.connector.connect(
        user="JORGEMS96",
        password="dJuniversidad.1",
        account="jrtuvgy-tq97242",
        warehouse="COMPUTE_WH",
        database="PROYECTO",
        role="ACCOUNTADMIN"
    )
 
    cursor = sf_conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT FICHERO_ORIGEN FROM PROYECTO.LANDING_PRODUCTOS.PRODUCTOS_SANITARIOS")
        ficheros_procesados = {row[0] for row in cursor.fetchall()}
    except Exception:
        ficheros_procesados = set()
    cursor.close()
 
    print(f"\n[PRODUCTOS CSV] Ficheros ya procesados en Snowflake: {len(ficheros_procesados)}")
    if ficheros_procesados:
        for f in sorted(ficheros_procesados):
            print(f"     - {f}")
 
    # 2. Listar ficheros disponibles en Azure Blob Storage
    sas_token = "sp=rl&st=2026-04-07T10:43:32Z&se=2026-06-30T18:58:32Z&sv=2025-11-05&sr=c&sig=2dhrhfePaVhLt0CEHAlogDUXteDSbdZDc1VM6xefJHI%3D"
    account_name = "sascvbootcamp"
    container_name = "productos"
 
    blob_service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=sas_token
    )
    container_client = blob_service.get_container_client(container_name)
    blobs = [b.name for b in container_client.list_blobs() if b.name.endswith(".csv")]
 
    print(f"\n[PRODUCTOS CSV] Ficheros disponibles en Azure Blob Storage: {len(blobs)}")
    for b in sorted(blobs):
        print(f"     - {b}")
 
    # 3. Filtrar solo los ficheros nuevos
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
 
    # 4. Procesar cada fichero nuevo
    directorio_seguro = os.path.join(tempfile.gettempdir(), "dlt_productos_limpio")
 
    pipeline = dlt.pipeline(
        pipeline_name="productos_to_landing",
        destination="snowflake",
        dataset_name="LANDING_PRODUCTOS",
        pipelines_dir=directorio_seguro
    )
 
    for fichero in ficheros_nuevos:
        print(f"\n  -> Procesando: {fichero}")
        blob_client = blob_service.get_blob_client(container=container_name, blob=fichero)
        content = blob_client.download_blob().readall().decode("utf-8")
        df = pd.read_csv(io.StringIO(content), sep=";")
        df["FICHERO_ORIGEN"] = fichero
 
        info = pipeline.run(
            df.to_dict(orient="records"),
            table_name="PRODUCTOS_SANITARIOS",
            write_disposition="append"
        )
 
        filas = sum(info.row_counts.values()) if hasattr(info, 'row_counts') and info.row_counts else len(df)
        print(f"     OK: {filas} filas cargadas.")
 
    sf_conn.close()
    fin = datetime.now()
    duracion = fin - inicio
    print(f"\n[PRODUCTOS CSV] Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[PRODUCTOS CSV] Duracion total: {duracion}")
    print(f"{'='*60}")












# ---------------------------------------------------------------
# MAIN
# Ejecutar una función cada vez cambiando el secrets.toml
# ---------------------------------------------------------------

if __name__ == '__main__':
    # Ejecutamos todo el pipeline de golpe (MEDICARE + NEXTBIO + PRODUCTOS CSV)
    load_medicare_landing()
    load_nextbio_landing()
    load_productos_landing()


