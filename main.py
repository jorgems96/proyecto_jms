#nota : no rallarse por la conexion a snowflake porque cuando termina la fase 1, la conexion finaliza y luego empieza la fase 2.

# main.py
import sys
sys.dont_write_bytecode = True
import os

# Registramos las carpetas de capa para que Python encuentre los modulos dentro de ellas
_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_BASE, 'LANDING'))
sys.path.insert(0, os.path.join(_BASE, 'RAW'))
sys.path.insert(0, os.path.join(_BASE, 'CLEANSED'))

import source_landing
import landing_raw
import raw_cleansed
import esquema_init

if __name__ == "__main__":
    
    #print("\n--- INICIANDO EJECUCIÓN DEL ORQUESTADOR ---")
    print("\n--- FASE 0: INICIALIZANDO ESQUEMA EN SNOWFLAKE ---")
    esquema_init.ejecutar_esquema()

    #FASE 1
    print("\n--- FASE 1: INICIANDO CAPA LANDING ---")
    source_landing.ejecutar_extraccion_completa()

    #FASE 2
    print("\n--- FASE 2: INICIANDO CAPA RAW ---")
    landing_raw.desplegar_capa_raw_automatica()


    #FASE 3
    print("\n--- FASE 3: INICIANDO CAPA CLEANSED ---")
    raw_cleansed.desplegar_capa_cleansed_automatica()

    #FASE 4
    print("\n--- FASE 4: INICIANDO CAPA CONFORMED ---")
    
    print("\nEjecución finalizada")
    

    