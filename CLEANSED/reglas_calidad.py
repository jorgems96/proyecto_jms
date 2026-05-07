# reglas_calidad.py
# Diccionario de reglas de calidad para la capa CLEANSED
# Nombres de columnas en MAYUSCULAS_CON_GUION_BAJO (formato Snowflake/dlt)
# Las filas que pasen las reglas se escriben en CLEANSED.NombreTabla
# Las filas que NO pasen se mandan a CLEANSED.NombreTabla_errors

import sys
sys.dont_write_bytecode = True # Evita la creación de archivos .pyc para mantener el proyecto limpio

# visitas ensayo lo del nivel
# ---------------------------------------------------------------

#Reglas reutilizables para varias tablas
NOT_NULL    = {"regla": "not_null"}
POSITIVE    = {"regla": "positive"}
NON_NEGATIVE = {"regla": "non_negative"}
REGEX_EMAIL = {"regla": "regex", "patron": r"^[^@]+@[^@]+\.[^@]+$"}
CLASE_RIESGO = {"regla": "allowed_values", "valores": ["I", "IIa", "IIb", "III"]}
NIVEL_1_4    = {"regla": "allowed_values", "valores": [1, 2, 3, 4]}


def allowed(valores):
    return {"regla": "allowed_values", "valores": valores}

def rango(minimo, maximo):
    return {"regla": "range", "min": minimo, "max": maximo}


# ---------------------------------------------------------------
# Reglas de calidad por tabla
# ---------------------------------------------------------------
REGLAS_CALIDAD = {


# CATALOGO: productos_sanitarios

    "productos_sanitarios": [
        {"columna": "CODIGO_PRODUCTO",       **NOT_NULL},
        {"columna": "NOMBRE_PRODUCTO",       **NOT_NULL},
        {"columna": "CLASE_RIESGO",          **CLASE_RIESGO},
        {"columna": "VIDA_UTIL_ANIOS",       **POSITIVE},
        {"columna": "PRECIO_REFERENCIA_EUR", **POSITIVE},
    ],


# SGC: especialidades

    "especialidades": [
        {"columna": "CODIGO_ESPECIALIDAD", **NOT_NULL},
        {"columna": "NOMBRE_ESPECIALIDAD", **NOT_NULL},
    ],


# SGC: medicos

    "medicos": [
        {"columna": "CODIGO_MEDICO",    **NOT_NULL},
        {"columna": "NOMBRE",           **NOT_NULL},
        {"columna": "APELLIDO1",        **NOT_NULL},
        {"columna": "NUMERO_COLEGIADO", **NOT_NULL},
        {"columna": "EMAIL",            **REGEX_EMAIL},
    ],


# SGC: pacientes

    "pacientes": [
        {"columna": "NUMERO_HISTORIA",  **NOT_NULL},
        {"columna": "NOMBRE",           **NOT_NULL},
        {"columna": "APELLIDO1",        **NOT_NULL},
        {"columna": "FECHA_NACIMIENTO", **NOT_NULL},
        {"columna": "SEXO",             **allowed(["M", "F", "O"])},
        {"columna": "GRUPO_SANGUINEO",  **allowed(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])},
        {"columna": "TIPO_COBERTURA",   **allowed(["BAS", "COM", "PRE"])},
        {"columna": "EMAIL",            **REGEX_EMAIL},
    ],


# SGC: diagnosticos_cie10

    "diagnosticos_cie10": [
        {"columna": "CODIGO_CIE10", **NOT_NULL},
        {"columna": "DESCRIPCION",  **NOT_NULL},
    ],


# SGC: paciente_diagnostico

    "paciente_diagnostico": [
        {"columna": "ID_PACIENTE",       **NOT_NULL},
        {"columna": "ID_DIAGNOSTICO",    **NOT_NULL},
        {"columna": "FECHA_DIAGNOSTICO", **NOT_NULL},
    ],


# SGC: ensayos_clinicos

    "ensayos_clinicos": [
        {"columna": "CODIGO_ENSAYO",          **NOT_NULL},
        {"columna": "TITULO_ENSAYO",          **NOT_NULL},
        {"columna": "FECHA_INICIO",           **NOT_NULL},
        {"columna": "ESTADO_ENSAYO",          **allowed(["PLN", "ACT", "COM", "SUS"])},
        {"columna": "OBJETIVO_RECLUTAMIENTO", **POSITIVE},
    ],


# SGC: participacion_ensayos

    "participacion_ensayos": [
        {"columna": "ID_ENSAYO",                  **NOT_NULL},
        {"columna": "ID_PACIENTE",                **NOT_NULL},
        {"columna": "FECHA_INICIO_PARTICIPACION", **NOT_NULL},
        {"columna": "FASE",                       **allowed(["F1", "F2", "F3", "F4"])},
        {"columna": "TIPO_CIEGO",                 **allowed(["AB", "SC", "DC"])},
        {"columna": "TIPO_ALEATORIZACION",        **allowed(["AL", "NA"])},
        {"columna": "GRUPO_ASIGNADO",             **allowed(["EXP", "CTR", "PLA"])},
        {"columna": "VIA_ADMINISTRACION",         **allowed(["ORL", "IV", "SC", "TOP", "INH"])},
    ],


# SGC: visitas_ensayo

    "visitas_ensayo": [
        {"columna": "ID_PARTICIPACION",        **NOT_NULL},
        {"columna": "FECHA_VISITA",            **NOT_NULL},
        {"columna": "NUMERO_VISITA",           **POSITIVE},
        {"columna": "NIVEL_EFICACIA",          **rango(0.0, 1.0)},
        {"columna": "DOSIS_ADMINISTRADA",      **POSITIVE},
        {"columna": "NUMERO_EFECTOS_ADVERSOS", **NON_NEGATIVE}, #PARA QUE SI TENGO UN 0, NO ME LO RECHACE PORQUE ES UN VALOR VÁLIDO, es lo mismo que mayor igual que cero
    ],


# SGC: monitorizaciones

    "monitorizaciones": [
        {"columna": "ID_PACIENTE",          **NOT_NULL},
        {"columna": "ID_MEDICO",            **NOT_NULL},
        {"columna": "CODIGO_EQUIPO",        **NOT_NULL},
        {"columna": "FECHA_MONITORIZACION", **NOT_NULL},
    ],


# SGC: lecturas_signos_vitales

    "lecturas_signos_vitales": [
        {"columna": "ID_MONITORIZACION",   **NOT_NULL},
        {"columna": "FRECUENCIA_CARDIACA", **rango(20, 300)},
        {"columna": "PRESION_SISTOLICA",   **rango(40, 300)},
        {"columna": "PRESION_DIASTOLICA",  **rango(20, 200)},
        {"columna": "TEMPERATURA",         **rango(30, 45)},
        {"columna": "SATURACION_OXIGENO",  **rango(50, 100)},
        {"columna": "NIVEL_GLUCOSA",       **rango(20, 600)},
    ],


# SGEB: departamentos

    "departamentos": [
        {"columna": "CODIGO_DEPARTAMENTO", **NOT_NULL},
        {"columna": "NOMBRE_DEPARTAMENTO", **NOT_NULL},
        {"columna": "EMAIL_DEPARTAMENTO",  **REGEX_EMAIL},
    ],


# SGEB: fabricantes

    "fabricantes": [
        {"columna": "CODIGO_FABRICANTE", **NOT_NULL},
        {"columna": "RAZON_SOCIAL",      **NOT_NULL},
        {"columna": "EMAIL_CONTACTO",    **REGEX_EMAIL},
    ],


# SGEB: ubicaciones

    "ubicaciones": [
        {"columna": "CODIGO_UBICACION", **NOT_NULL},
        {"columna": "EDIFICIO",         **NOT_NULL},
        {"columna": "SALA",             **NOT_NULL},
        {"columna": "TIPO_SALA",        **allowed(["Quirófano", "UCI", "Consulta", "Laboratorio", "Almacén"])}, #para que no me salte error con las tildes
        {"columna": "CAPACIDAD",        **POSITIVE},
    ],


# SGEB: equipos

    "equipos": [
        {"columna": "CODIGO_EQUIPO",      **NOT_NULL},
        {"columna": "NOMBRE_EQUIPO",      **NOT_NULL},
        {"columna": "NUMERO_SERIE",       **NOT_NULL},
        {"columna": "ID_FABRICANTE",      **NOT_NULL},
        {"columna": "ID_DEPARTAMENTO",    **NOT_NULL},
        {"columna": "ID_UBICACION",       **NOT_NULL},
        {"columna": "ESTADO_CODIGO",      **NIVEL_1_4},
        {"columna": "CLASE_RIESGO",       **CLASE_RIESGO},
        {"columna": "PRECIO_ADQUISICION", **POSITIVE},
    ],


# SGEB: tecnicos

    "tecnicos": [
        {"columna": "CODIGO_EMPLEADO",      **NOT_NULL},
        {"columna": "NOMBRE_TECNICO",       **NOT_NULL},
        {"columna": "ID_DEPARTAMENTO",      **NOT_NULL},
        {"columna": "NIVEL_CERTIFICACION",  **NIVEL_1_4},
        {"columna": "TARIFA_HORA",          **POSITIVE},
        {"columna": "EMAIL_CORPORATIVO",    **REGEX_EMAIL},
    ],


# SGEB: ordenes_mantenimiento

    "ordenes_mantenimiento": [
        {"columna": "NUMERO_ORDEN",       **NOT_NULL},
        {"columna": "ID_EQUIPO",          **NOT_NULL},
        {"columna": "ID_TECNICO",         **NOT_NULL},
        {"columna": "TIPO_MANTENIMIENTO", **allowed(["PREV", "CORR", "CALIB", "INSP"])},
        {"columna": "PRIORIDAD",          **rango(1, 4)},
        {"columna": "GRAVEDAD",           **rango(1, 3)},
        {"columna": "HORAS_TRABAJADAS",   **POSITIVE},
    ],


# SGEB: consumo_repuestos

    "consumo_repuestos": [
        {"columna": "ID_ORDEN",                   **NOT_NULL},
        {"columna": "ID_REPUESTO",                **NOT_NULL},
        {"columna": "CANTIDAD",                   **POSITIVE},
        {"columna": "PRECIO_UNITARIO_EN_MOMENTO", **POSITIVE},
    ],


# SGEB: repuestos

    "repuestos": [
        {"columna": "CODIGO_REPUESTO", **NOT_NULL},
        {"columna": "NOMBRE_REPUESTO", **NOT_NULL},
        {"columna": "PRECIO_UNITARIO", **POSITIVE},
    ],


# SGEB: categoria_equipos

    "categoria_equipos": [
        {"columna": "CODIGO_CATEGORIA", **NOT_NULL},
        {"columna": "NOMBRE_CATEGORIA", **NOT_NULL},
    ],


# SGEB: planificacion_preventivos

    "planificacion_preventivos": [
        {"columna": "ID_EQUIPO",         **NOT_NULL},
        {"columna": "FECHA_PLANIFICADA", **NOT_NULL},
    ],
}