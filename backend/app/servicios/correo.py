"""Envio de correos con un proveedor intercambiable.

En desarrollo el correo se imprime en la terminal (CORREO_PROVEEDOR=consola).
En el despliegue sale por Amazon SES (CORREO_PROVEEDOR=ses). Si el envio falla,
se anota en el registro y la operacion sigue: un correo nunca debe tumbar una
solicitud ni un registro.
"""

import logging
from functools import lru_cache

import boto3

from app.core.config import configuracion

registro = logging.getLogger("uvicorn.error")


class CorreoConsola:
    def enviar(self, destinatario: str, asunto: str, texto: str) -> None:
        print("\n" + "=" * 70)
        print(f"CORREO PARA {destinatario}: {asunto}")
        print(texto)
        print("=" * 70 + "\n")


class CorreoSES:
    def __init__(self, cliente, remitente: str):
        self.cliente = cliente
        self.remitente = remitente

    def enviar(self, destinatario: str, asunto: str, texto: str) -> None:
        self.cliente.send_email(
            FromEmailAddress=self.remitente,
            Destination={"ToAddresses": [destinatario]},
            Content={
                "Simple": {
                    "Subject": {"Data": asunto, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": texto, "Charset": "UTF-8"}},
                }
            },
        )


@lru_cache
def obtener_proveedor():
    if configuracion.correo_proveedor != "ses":
        return CorreoConsola()
    llaves = {}
    if configuracion.aws_access_key_id:
        llaves = {
            "aws_access_key_id": configuracion.aws_access_key_id,
            "aws_secret_access_key": configuracion.aws_secret_access_key,
        }
    cliente = boto3.client("sesv2", region_name=configuracion.aws_region, **llaves)
    return CorreoSES(cliente, configuracion.correo_remitente)


def enviar(destinatario: str, asunto: str, texto: str) -> bool:
    # Devuelve si salio; un fallo solo se anota.
    try:
        obtener_proveedor().enviar(destinatario, asunto, texto)
        return True
    except Exception:
        registro.exception("No se pudo enviar el correo a %s", destinatario)
        return False