# datos.py
import sys
sys.dont_write_bytecode = True
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------
# FUENTE 1: MEDICARE (Azure SQL Server)
# Clave: nombre de la tabla en el origen (SQL Server)
# Valor: nombre de la tabla en LANDING_MEDICARE (Snowflake, minúsculas)
# ---------------------------------------------------------------
SCHEMA_LANDING_MEDICARE = "LANDING_MEDICARE"
CAMPO_CURSOR_MEDICARE_SNOWFLAKE = "FECHA_MODIFICACION"
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
AZURE_CONTAINER_NAME = "productos"

