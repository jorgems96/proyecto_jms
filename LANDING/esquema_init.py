import os
import sys
import re
from conexiones import get_snowflake_connection
sys.dont_write_bytecode = True

_DIR  = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_DIR)

# Ficheros SQL para inicializar el esquema y SPs de cada capa. (sin crear objetos de capa CONFORMED, ni las vistas de OPTIMIZED, eso viene luego en cada capa)
# El orden es importante: primero se crean los esquemas y objetos comunes, luego los específicos de cada capa.
# Se ejecutan en orden.
_FICHEROS_SETUP = [
    os.path.join(_DIR,  'ESQUEMA.sql'),                           # esquemas de Snowflake
    os.path.join(_ROOT, 'RAW',      'sp_deploy_raw.sql'),         # SP capa RAW
    os.path.join(_ROOT, 'CLEANSED', 'reglas_calidad.sql'),        # tabla de reglas de calidad
    os.path.join(_ROOT, 'CLEANSED', 'sp_deploy_cleansed.sql'),    # SP capa CLEANSED
    os.path.join(_ROOT, 'CONFORMED', 'sp_scd_conformed.sql'),     # SPs genericos SCD1/SCD2 para dimensiones
    os.path.join(_ROOT, 'CONFORMED', 'sp_load_conformed.sql'),     # SP_LOAD_* de dimensiones y hechos
    os.path.join(_ROOT, 'CONFORMED', 'sp_deploy_conformed.sql'),  # DDL tablas + SP_DEPLOY_CONFORMED
    os.path.join(_ROOT, 'UTILS',     'control_tasks.sql'),          # SPs para activar/suspender tasks
    os.path.join(_ROOT, 'OPTIMIZED', 'sp_deploy_optimized.sql'),  # CREATE SCHEMA + SP vistas
]


def _sentencias(sql):
    """
    Divide SQL en sentencias individuales para cursor.execute().

    El conector de Python tiene un comportamiento no documentado con $$ que
    extrae el cuerpo del SP y lo envia como sentencia separada (sin la cabecera
    CREATE PROCEDURE), provocando errores de sintaxis. Para evitarlo, convertimos
    los bloques $$...$$ a comillas simples '...' en memoria antes de enviarlos.
    Los ficheros .sql originales no se modifican.

    Pasos:
      1. Convierte cada bloque $$...$$  a  '...' escapando las ' internas como ''
      2. Divide el SQL resultante por ; respetando strings entre comillas simples
      3. Filtra fragmentos que solo contengan comentarios
    """
    # -- Paso 1: convertir $$ a comillas simples
    partes = re.split(r'\$\$(.*?)\$\$', sql, flags=re.DOTALL)
    reconstruido = ''
    for i, parte in enumerate(partes):
        if i % 2 == 0:
            reconstruido += parte          # texto normal
        else:
            reconstruido += "'" + parte.replace("'", "''") + "'"  # cuerpo SP

    # -- Paso 2: dividir por ; respetando strings y comentarios --
    resultado = []
    actual    = []
    in_str    = False
    in_comment = False
    i, n      = 0, len(reconstruido)

    while i < n:
        c = reconstruido[i]

        if c == '\n':
            in_comment = False
            actual.append(c)

        elif in_comment:
            actual.append(c)

        elif c == '-' and not in_str and i + 1 < n and reconstruido[i + 1] == '-':
            in_comment = True
            actual.append(c)

        elif c == "'" and not in_str:
            in_str = True
            actual.append(c)

        elif c == "'" and in_str:
            if i + 1 < n and reconstruido[i + 1] == "'":
                actual.append("''")        # comilla escapada, quedamos en string
                i += 2
                continue
            else:
                in_str = False
                actual.append(c)

        elif c == ';' and not in_str:
            stmt = ''.join(actual).strip()
            lineas_sql = [l for l in stmt.split('\n')
                          if l.strip() and not l.strip().startswith('--')]
            if lineas_sql:
                resultado.append(stmt)
            actual = []

        else:
            actual.append(c)

        i += 1

    # Remanente sin ; final (p.ej. comentario al final del fichero)
    stmt = ''.join(actual).strip()
    lineas_sql = [l for l in stmt.split('\n')
                  if l.strip() and not l.strip().startswith('--')]
    if lineas_sql:
        resultado.append(stmt)

    return resultado


def ejecutar_esquema():
    conn = get_snowflake_connection()
    try:
        for ruta in _FICHEROS_SETUP:
            with open(ruta, encoding='utf-8') as f:
                sql = f.read()
            for sentencia in _sentencias(sql):
                conn.cursor().execute(sentencia)
            print(f"  OK: {os.path.basename(ruta)}")
        print("Esquema inicializado correctamente.")
    finally:
        conn.close()
