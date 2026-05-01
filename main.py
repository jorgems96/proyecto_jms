#nota : no rallarse por la conexion a snowflake porque cuando termina la fase 1, la conexion finaliza y luego empieza la fase 2.

# main.py
import source_landing
import landing_raw
import raw_cleansed
import esquema_init

if __name__ == "__main__":
    esquema_init.ejecutar_esquema()

    #FASE 1
    #print("\n--- FASE 1: INICIANDO CAPA LANDING ---")
    source_landing.ejecutar_extraccion_completa()

    #FASE 2
    print("\n--- FASE 2: INICIANDO CAPA RAW ---")
    landing_raw.desplegar_capa_raw_automatica()


    #FASE 3
    print("\n--- FASE 3: INICIANDO CAPA CLEANSED ---")
    raw_cleansed.desplegar_capa_cleansed_automatica()

    print("\nEjecución finalizada")
    