# ---------------------------------------------------------------
# config.py
# Constantes y configuración del proyecto
# Tablas, schemas, credenciales y parámetros de conexión


# ---------------------------------------------------------------

# ---------------------------------------------------------------
# SNOWFLAKE
# ---------------------------------------------------------------
SNOWFLAKE_USER     = "JORGEMS96"
SNOWFLAKE_PASSWORD = "dJuniversidad.1"
SNOWFLAKE_ACCOUNT  = "jrtuvgy-tq97242"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
SNOWFLAKE_DATABASE = "PROYECTO"
SNOWFLAKE_ROLE     = "ACCOUNTADMIN"

# ---------------------------------------------------------------
# FUENTE 1: MEDICARE (Azure SQL Server)
# Clave: nombre de la tabla en el origen (SQL Server)
# Valor: nombre de la tabla en LANDING_MEDICARE (Snowflake, minúsculas)
# ---------------------------------------------------------------
SCHEMA_LANDING_MEDICARE = "LANDING_MEDICARE"
# Para consultar el watermark en Snowflake (donde dlt normaliza a mayúsculas con guión bajo)
CAMPO_CURSOR_MEDICARE_SNOWFLAKE = "FECHA_MODIFICACION"
# Para el cursor de dlt (nombre original en SQL Server)
CAMPO_CURSOR_MEDICARE_ORIGEN = "FechaModificacion"

TABLAS_MEDICARE = {
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

# ---------------------------------------------------------------
# FUENTE 2: NEXTBIO (PostgreSQL)
# Clave: nombre de la tabla en el origen (PostgreSQL)
# Valor: nombre de la tabla en LANDING_NEXTBIO (Snowflake, mayúsculas para watermark)
# ---------------------------------------------------------------
SCHEMA_LANDING_NEXTBIO  = "LANDING_NEXTBIO"
CAMPO_CURSOR_NEXTBIO    = "fecha_modificacion"

TABLAS_NEXTBIO = {
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

# ---------------------------------------------------------------
# FUENTE 3: CSV PRODUCTOS SANITARIOS (Azure Blob Storage)
# ---------------------------------------------------------------
SCHEMA_LANDING_PRODUCTOS = "LANDING_PRODUCTOS"
TABLA_PRODUCTOS          = "PRODUCTOS_SANITARIOS"

AZURE_ACCOUNT_NAME   = "sascvbootcamp"
AZURE_CONTAINER_NAME = "productos"
AZURE_SAS_TOKEN      = "sp=rl&st=2026-04-07T10:43:32Z&se=2026-06-30T18:58:32Z&sv=2025-11-05&sr=c&sig=2dhrhfePaVhLt0CEHAlogDUXteDSbdZDc1VM6xefJHI%3D"
