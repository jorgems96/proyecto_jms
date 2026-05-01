import os
from conexiones import get_snowflake_connection


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
