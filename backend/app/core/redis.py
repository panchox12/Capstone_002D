"""Conexion a Redis, el almacen en memoria del proyecto.

Redis guarda datos que deben borrarse solos despues de un tiempo, como la
marca de "en linea" de cada usuario. PostgreSQL no tiene esa capacidad.
"""

from functools import lru_cache

import redis

from app.core.config import configuracion


@lru_cache
def _cliente() -> redis.Redis:
    # decode_responses=True: Redis devuelve textos de Python en vez de bytes.
    # Los tiempos maximos evitan que una pagina quede colgada si Redis se cae.
    return redis.Redis.from_url(
        configuracion.redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def obtener_redis() -> redis.Redis:
    """Dependencia de FastAPI. Las pruebas la reemplazan por un Redis falso en memoria."""
    return _cliente()
