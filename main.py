import sys
sys.dont_write_bytecode = True
import os

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_BASE, 'LANDING'))

import source_landing
import esquema_init
from conexiones import get_snowflake_connection

# Dimensiones y hechos disponibles para ejecucion individual
_CONFORMED_OBJETOS = [
    'DIM_FECHA', 'DIM_DEPARTAMENTO', 'DIM_UBICACION', 'DIM_FABRICANTE',
    'DIM_MEDICO', 'DIM_TECNICO', 'DIM_PACIENTE', 'DIM_EQUIPO',
    'DIM_ENSAYO', 'DIM_DIAGNOSTICO',
    'DIM_PERFIL_MANTENIMIENTO', 'DIM_PERFIL_ENSAYO',
    'FACT_MANTENIMIENTO_EQUIPOS', 'FACT_MONITORIZACION_PACIENTES', 'FACT_ENSAYOS_CLINICOS',
]

def _ejecutar_sql(conn, sql, descripcion):
    conn.cursor().execute(sql)
    print(f"  {descripcion} completado correctamente.")


def fase0():
    print("\n--- FASE 0: INICIALIZANDO ESQUEMA ---")
    esquema_init.ejecutar_esquema()


def fase1():
    print("\n--- FASE 1: SOURCE → LANDING ---")
    source_landing.ejecutar_extraccion_completa()


def fase2():
    print("\n--- FASE 2: CAPA RAW ---")
    conn = get_snowflake_connection()
    try:
        _ejecutar_sql(conn, "CALL RAW.SP_DEPLOY_RAW()", "Capa RAW")
    finally:
        conn.close()


def fase3():
    print("\n--- FASE 3: CAPA CLEANSED ---")
    conn = get_snowflake_connection()
    try:
        _ejecutar_sql(conn, "CALL CLEANSED.SP_DEPLOY_CLEANSED()", "Capa CLEANSED")
    finally:
        conn.close()


def fase4():
    print("\n--- FASE 4: CAPA CONFORMED ---")
    conn = get_snowflake_connection()
    try:
        _ejecutar_sql(conn, "CALL CONFORMED.SP_DEPLOY_CONFORMED()", "Capa CONFORMED")
    finally:
        conn.close()


def fase4_objeto(nombre):
    print(f"\n--- EXTRA: CARGANDO {nombre} ---")
    conn = get_snowflake_connection()
    try:
        _ejecutar_sql(conn, f"CALL CONFORMED.SP_LOAD_{nombre}()", nombre)
    finally:
        conn.close()


def menu_objeto():
    print("\nSelecciona dimension o hecho:")
    for i, obj in enumerate(_CONFORMED_OBJETOS, 1):
        print(f"  {i:2}. {obj}")
    try:
        idx = int(input("Opcion: ").strip()) - 1
        if 0 <= idx < len(_CONFORMED_OBJETOS):
            return _CONFORMED_OBJETOS[idx]
    except ValueError:
        pass
    print("  Opcion no valida.")
    return None


def fase5():
    print("\n--- FASE 5: CAPA OPTIMIZED ---")
    conn = get_snowflake_connection()
    try:
        _ejecutar_sql(conn, "CALL OPTIMIZED.SP_DEPLOY_OPTIMIZED()", "Capa OPTIMIZED")
    finally:
        conn.close()


def fase9():
    print("\n--- DROP DATABASE PROYECTO ---")
    print("  ATENCION: esto eliminara la base de datos entera de forma IRREVERSIBLE.")
    confirmacion = input("  Escribe CONFIRMAR para continuar: ").strip()
    if confirmacion != "CONFIRMAR":
        print("  Operacion cancelada.")
        return
    conn = get_snowflake_connection()
    try:
        _ejecutar_sql(conn, "DROP DATABASE IF EXISTS PROYECTO", "DROP DATABASE PROYECTO")
    finally:
        conn.close()


def menu_principal():
    print("\n========================================")
    print("   ORQUESTADOR — PROYECTO JMS  ")
    print("========================================")
    print("  [1] Ejecucion completa  (ESQUEMAS + LANDING + RAW + CLEANSED + CONFORMED + OPTIMIZED)")
    print("  [2] FASE 0  - ESQUEMAS Y PROCEDIMIENTOS ALMACENADOS")
    print("  [3] FASE 1  - CAPA LANDING (source → landing, extraccion incremental)")
    print("  [4] FASE 2  - CAPA RAW (ultimo estado)")
    print("  [5] FASE 3  - CAPA CLEANSED (limpieza y transformacion)")
    print("  [6] FASE 4  - CAPA CONFORMED (todas las dimensiones y hechos)")
    print("  [7] FASE 5  - CAPA OPTIMIZED (vistas)")
    print("  [8] EXTRA   - CONFORMED: dimension o hecho individual")
    print("  [9] DROP    - Eliminar base de datos completa")
    print("  [0] Salir")
    return input("Selecciona opcion: ").strip()


if __name__ == "__main__":
    while True:
        opcion = menu_principal()

        if opcion == '0':
            print("Saliendo.")
            break

        elif opcion == '1':
            fase0()
            fase1()
            fase2()
            fase3()
            fase4()
            fase5()
            print("\nEjecucion completa finalizada.")

        elif opcion == '2':
            fase0()

        elif opcion == '3':
            fase1()

        elif opcion == '4':
            fase2()

        elif opcion == '5':
            fase3()

        elif opcion == '6':
            fase4()

        elif opcion == '7':
            fase5()

        elif opcion == '8':
            obj = menu_objeto()
            if obj:
                fase4_objeto(obj)

        elif opcion == '9':
            fase9()

        else:
            print("  Opcion no valida, intenta de nuevo.")



# EXECUTE TASK CONFORMED.TASK_CONFORMED_ROOT;
#dag completo para ejecutar de golpe  todas las dimensiones en snowflake, pero se recomienda ejecutar por fases para validar cada una de ellas