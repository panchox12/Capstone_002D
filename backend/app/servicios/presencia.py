"""Presencia en linea.

Mientras el usuario tiene Cachai abierto, el navegador envia un latido cada
30 segundos. Cada latido guarda en Redis una marca que se borra sola a los
70 segundos. Si llegan latidos, la marca se renueva; si el usuario cierra la
pestana o pierde la conexion, la marca desaparece sola y queda desconectado.
Nadie tiene que acordarse de "desconectarlo".
"""

import logging
import uuid

import redis

SEGUNDOS_SIN_SENAL = 70
PREFIJO = "presencia:"

registro = logging.getLogger("uvicorn.error")


def _clave(usuario_id: uuid.UUID) -> str:
    return f"{PREFIJO}{usuario_id}"


def marcar_en_linea(r: redis.Redis, usuario_id: uuid.UUID) -> None:
    r.set(_clave(usuario_id), "1", ex=SEGUNDOS_SIN_SENAL)


def marcar_desconectado(r: redis.Redis, usuario_id: uuid.UUID) -> None:
    r.delete(_clave(usuario_id))


def esta_en_linea(r: redis.Redis, usuario_id: uuid.UUID) -> bool:
    return usuario_id in en_linea(r, [usuario_id])


def en_linea(r: redis.Redis, usuarios: list[uuid.UUID]) -> set[uuid.UUID]:
    """De una lista de usuarios, cuales estan en linea. Una sola consulta a Redis."""
    if not usuarios:
        return set()
    try:
        valores = r.mget([_clave(usuario_id) for usuario_id in usuarios])
    except redis.RedisError:
        # Si Redis no responde, nadie aparece en linea: es mejor que caerse.
        registro.warning("Redis no responde: la presencia se muestra como desconectada")
        return set()
    return {usuario_id for usuario_id, valor in zip(usuarios, valores) if valor is not None}
