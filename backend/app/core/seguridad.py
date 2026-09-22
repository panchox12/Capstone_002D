"""Funciones de seguridad: hasheo de contrasenas y tokens JWT."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import configuracion

# bcrypt trunca silenciosamente cualquier entrada sobre 72 bytes.
# Truncamos explicitamente para que el comportamiento sea visible y predecible.
LIMITE_BYTES_BCRYPT = 72

RONDAS_BCRYPT = 12


def hashear_contrasena(texto_plano: str) -> str:
    """Convierte una contrasena en un hash bcrypt listo para guardar."""
    bytes_contrasena = texto_plano.encode("utf-8")[:LIMITE_BYTES_BCRYPT]
    sal = bcrypt.gensalt(rounds=RONDAS_BCRYPT)
    return bcrypt.hashpw(bytes_contrasena, sal).decode("utf-8")


def verificar_contrasena(texto_plano: str, hash_guardado: str) -> bool:
    """Compara una contrasena en texto plano contra un hash almacenado."""
    bytes_contrasena = texto_plano.encode("utf-8")[:LIMITE_BYTES_BCRYPT]
    try:
        return bcrypt.checkpw(bytes_contrasena, hash_guardado.encode("utf-8"))
    except ValueError:
        # El hash guardado esta corrupto o no tiene formato.
        return False


# ---------------------------------------------------------------------------
# Tokens JWT
# ---------------------------------------------------------------------------

TIPO_ACCESO = "acceso"
TIPO_CONFIRMACION = "confirmacion_correo"


def crear_token(
    sujeto: str,
    tipo: str = TIPO_ACCESO,
    minutos_vigencia: int | None = None,
) -> str:
    """Crea un token firmado.

    sujeto: el identificador del usuario, como texto.
    tipo: para que sirve este token. Un token de confirmacion de correo
          NO debe poder usarse como token de acceso.
    """
    ahora = datetime.now(timezone.utc)
    minutos = minutos_vigencia or configuracion.minutos_expiracion_token

    carga: dict[str, Any] = {
        "sub": sujeto,
        "tipo": tipo,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos),
    }

    return jwt.encode(
        carga,
        configuracion.secret_key,
        algorithm=configuracion.algoritmo_jwt,
    )


def decodificar_token(token: str, tipo_esperado: str = TIPO_ACCESO) -> dict[str, Any]:
    """Verifica toda la información. Lanza excepcion si algo falla.

    Excepciones posibles:
      jwt.ExpiredSignatureError  -> el token vencio
      jwt.InvalidTokenError      -> firma invalida, formato malo o tipo incorrecto
    """
    carga = jwt.decode(
        token,
        configuracion.secret_key,
        algorithms=[configuracion.algoritmo_jwt],
    )

    if carga.get("tipo") != tipo_esperado:
        raise jwt.InvalidTokenError("Tipo de token incorrecto")

    return carga