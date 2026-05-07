import os
import sys
from conexiones import get_snowflake_connection
sys.dont_write_bytecode = True # Evita la creación de archivos .pyc para mantener el proyecto limpio

# Esta funcion Ejecuta el script ESQUEMA.sql para crear el esquema en Snowflake
def ejecutar_esquema():
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ESQUEMA.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    sentencias = [s.strip() for s in contenido.split(";") if s.strip()]
    conn = get_snowflake_connection()
    try:
        for sentencia in sentencias:
            conn.execute_string(sentencia)
        print("Esquema inicializado correctamente.")
    finally:
        conn.close()
