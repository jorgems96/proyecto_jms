# conexiones.py
import dlt
import snowflake.connector

def get_snowflake_connection():
    """
    Obtiene una conexión a Snowflake utilizando las credenciales 
    centralizadas en .dlt/secrets.toml.
    """
    # dlt busca automáticamente en .dlt/secrets.toml
    sn_creds = dlt.secrets.get("destination.snowflake.credentials")
    
    if not sn_creds:
        raise ValueError("No se encontraron credenciales de Snowflake en secrets.toml")

    return snowflake.connector.connect(
        user=sn_creds["username"],
        password=sn_creds["password"],
        account=sn_creds["host"],
        warehouse=sn_creds["warehouse"],
        database=sn_creds["database"],
        role=sn_creds["role"]
    )

