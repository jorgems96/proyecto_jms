import sys
sys.dont_write_bytecode = True
import os
import shutil
import time


_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_BASE, 'LANDING'))
sys.path.insert(0, os.path.join(_BASE, 'UTILS'))

import source_landing
import esquema_init
from conexiones import get_snowflake_connection

_CONFORMED_OBJETOS = [
    'DIM_FECHA', 'DIM_DEPARTAMENTO', 'DIM_UBICACION', 'DIM_FABRICANTE',
    'DIM_MEDICO', 'DIM_TECNICO', 'DIM_PACIENTE', 'DIM_EQUIPO',
    'DIM_ENSAYO', 'DIM_DIAGNOSTICO',
    'DIM_PERFIL_MANTENIMIENTO', 'DIM_PERFIL_ENSAYO',
    'FACT_MANTENIMIENTO_EQUIPOS', 'FACT_MONITORIZACION_PACIENTES', 'FACT_ENSAYOS_CLINICOS',
]

_DLT_TEMP_DIRS = [
    r"C:\dlt_temp\medicare",
    r"C:\dlt_temp\nextbio",
    r"C:\dlt_temp\productos",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ejecutar_sql(conn, sql, descripcion):
    conn.cursor().execute(sql)
    print(f"  {descripcion} completado correctamente.")


def _snowflake(sql, descripcion):
    conn = get_snowflake_connection()
    try:
        _ejecutar_sql(conn, sql, descripcion)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fases del pipeline
# ---------------------------------------------------------------------------

# para medir la duracion de cada fase, formateando el resultado en segundos o minutos + segundos si supera 60s
def _duracion(t0):
    segundos = time.perf_counter() - t0
    return f"{segundos:.1f}s" if segundos < 60 else f"{int(segundos)//60}m {int(segundos)%60}s"


def fase0():
    print("\n--- FASE 0: ESQUEMAS Y PROCEDIMIENTOS ALMACENADOS ---")
    t0 = time.perf_counter()
    esquema_init.ejecutar_esquema()
    print(f"  Duracion FASE 0: {_duracion(t0)}")


def fase1():
    print("\n--- FASE 1: SOURCE → LANDING ---")
    t0 = time.perf_counter()
    source_landing.ejecutar_extraccion_completa()
    print(f"  Duracion FASE 1: {_duracion(t0)}")


def fase2():
    print("\n--- FASE 2: CAPA RAW ---")
    t0 = time.perf_counter()
    _snowflake("CALL RAW.SP_DEPLOY_RAW()", "Capa RAW")
    print(f"  Duracion FASE 2: {_duracion(t0)}")


def fase3():
    print("\n--- FASE 3: CAPA CLEANSED ---")
    t0 = time.perf_counter()
    _snowflake("CALL CLEANSED.SP_DEPLOY_CLEANSED()", "Capa CLEANSED")
    print(f"  Duracion FASE 3: {_duracion(t0)}")


def fase4():
    print("\n--- FASE 4: CAPA CONFORMED ---")
    t0 = time.perf_counter()
    _snowflake("CALL CONFORMED.SP_DEPLOY_CONFORMED()", "Capa CONFORMED")
    print(f"  Duracion FASE 4: {_duracion(t0)}")


def fase5():
    print("\n--- FASE 5: CAPA OPTIMIZED ---")
    t0 = time.perf_counter()
    _snowflake("CALL OPTIMIZED.SP_DEPLOY_OPTIMIZED()", "Capa OPTIMIZED")
    print(f"  Duracion FASE 5: {_duracion(t0)}")


def cargar_objeto_conformed(nombre):
    print(f"\n--- EXTRA: CARGANDO {nombre} ---")
    _snowflake(f"CALL CONFORMED.SP_LOAD_{nombre}()", nombre)


def activar_tasks():
    print("\n--- ACTIVAR TASKS (CARGA INCREMENTAL CDC) ---")
    t0 = time.perf_counter()
    _snowflake("CALL RAW.SP_ACTIVAR_TASKS()",       "RAW tasks activados")
    _snowflake("CALL CLEANSED.SP_ACTIVAR_TASKS()",  "CLEANSED tasks activados")
    _snowflake("CALL CONFORMED.SP_ACTIVAR_TASKS()", "CONFORMED tasks activados")
    print(f"  Duracion TASKS: {_duracion(t0)}")


def suspender_tasks():
    print("\n--- SUSPENDER TASKS (PARAR CARGA INCREMENTAL CDC) ---")
    t0 = time.perf_counter()
    _snowflake("CALL RAW.SP_SUSPENDER_TASKS()",       "RAW tasks suspendidos")
    _snowflake("CALL CLEANSED.SP_SUSPENDER_TASKS()",  "CLEANSED tasks suspendidos")
    _snowflake("CALL CONFORMED.SP_SUSPENDER_TASKS()", "CONFORMED tasks suspendidos")
    print(f"  Duracion TASKS: {_duracion(t0)}")


# ---------------------------------------------------------------------------
# Reset completo del proyecto
# ---------------------------------------------------------------------------

def drop_proyecto():
    print("\n--- RESET COMPLETO DEL PROYECTO ---")
    print("  ATENCION: eliminara la base de datos Snowflake y las carpetas dlt_temp de forma IRREVERSIBLE.")
    if input("  Escribe CONFIRMAR para continuar: ").strip() != "CONFIRMAR":
        print("  Operacion cancelada.")
        return
    _snowflake("DROP DATABASE IF EXISTS PROYECTO", "DROP DATABASE PROYECTO")
    for carpeta in _DLT_TEMP_DIRS:
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
            print(f"  Carpeta eliminada: {carpeta}")
        else:
            print(f"  Carpeta no existia: {carpeta}")


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

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


def menu_principal():
    print("\n========================================")
    print("   ORQUESTADOR — PROYECTO JMS  ")
    print("========================================")
    print("  [1] Ejecucion completa  (TODAS LAS FASES)")
    print("  [2] FASE 0  - Esquemas y procedimientos almacenados")
    print("  [3] FASE 1  - Capa LANDING  (source → landing, incremental)")
    print("  [4] FASE 2  - Capa RAW      (ultimo estado)")
    print("  [5] FASE 3  - Capa CLEANSED (limpieza y transformacion)")
    print("  [6] FASE 4  - Capa CONFORMED (dimensiones y hechos)")
    print("  [7] FASE 5  - Capa OPTIMIZED (vistas)")
    print("  [8] EXTRA   - Cargar dimension o hecho individual (CONFORMED)")
    print("  [A] TASKS   - Activar todos los tasks (carga incremental CDC)")
    print("  [S] TASKS   - Apagar todos los tasks (parar consumo de creditos)")
    print("  [9] RESET   - Eliminar base de datos y carpetas dlt_temp")
    print("  [0] Salir")
    return input("Selecciona opcion: ").strip()


if __name__ == "__main__":
    while True:
        opcion = menu_principal()

        if opcion == '0':
            print("Saliendo.")
            break
        elif opcion == '1':
            t_total = time.perf_counter()
            fase0(); fase1(); fase2(); fase3(); fase4(); fase5(); activar_tasks()
            print(f"\nEjecucion completa finalizada. Duracion total: {_duracion(t_total)}")
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
                cargar_objeto_conformed(obj)
        elif opcion.upper() == 'A':
            activar_tasks()
        elif opcion.upper() == 'S':
            suspender_tasks()
        elif opcion == '9':
            drop_proyecto()
        else:
            print("  Opcion no valida, intenta de nuevo.")
