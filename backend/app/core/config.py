"""Configuracion central de la aplicacion.

Toda la configuracion entra por variables de entorno. En desarrollo esas
variables se leen desde el archivo .env; en produccion las inyecta AWS.
El codigo es identico en ambos casos.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """Define que variables existen, de que tipo son y cual es su valor por defecto."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicacion ---
    app_nombre: str = "Cachai"
    app_entorno: str = "desarrollo"
    app_debug: bool = False

    # --- Base de datos ---
    database_url: str

    # --- Cache ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Seguridad ---
    secret_key: str
    algoritmo_jwt: str = "HS256"
    minutos_expiracion_token: int = 60

    @property
    def es_desarrollo(self) -> bool:
        return self.app_entorno == "desarrollo"


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve siempre la misma instancia, gracias al cache."""
    return Configuracion()


configuracion = obtener_configuracion()