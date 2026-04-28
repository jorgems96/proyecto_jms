#nota : no rallarse por la conexion a snowflake porque cuando termina la fase 1, la conexion finaliza y luego empieza la fase 2. 

# main.py
import source_landing   # Estilo consistente
import landing_raw      # Estilo consistente
import raw_cleansed     # Estilo consistente

if __name__ == "__main__":
    #print("🚀 INICIANDO EL PIPELINE DE DATOS 🚀")

    # FASE 1: Independiente (Ella misma se conecta y se cierra)
    #print("\n--- FASE 1: EXTRACCIÓN A LANDING ---")
    #source_landing.ejecutar_extraccion_completa()

    # FASE 2: Independiente (Ella misma se conecta y se cierra)
    print("\n--- FASE 2: DESPLIEGUE DE CAPA RAW ---")
    landing_raw.desplegar_capa_raw_automatica()


    # FASE 3: Independiente (Ella misma se conecta y se cierra)
    print("\n--- FASE 3: DESPLIEGUE DE CAPA CLEANSED ---")
    raw_cleansed.desplegar_capa_cleansed_automatica()

    print("\nEjecución finalizada")
    