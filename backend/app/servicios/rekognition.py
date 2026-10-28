"""Proveedor real de verificacion de identidad: Amazon Rekognition.

Se usa solo con PROVEEDOR_IDENTIDAD=aws. Las imagenes viajan a AWS
dentro de la peticion y no se guardan en ningun bucket. La cuenta de AWS tiene
la politica de exclusion de servicios de IA, para que AWS no las use para
entrenar sus modelos.
"""

import re
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import configuracion
from app.servicios.verificacion import ProveedorNoDisponible

# RUN con o sin puntos y guion: 12.345.678-5, 12345678-5 o 123456785.
PATRON_RUN = re.compile(r"\b(\d{1,2}\.?\d{3}\.?\d{3})\s*-?\s*([\dkK])\b")

# Errores que significan "la imagen no sirve", no "AWS no responde".
ERRORES_DE_IMAGEN = {"InvalidParameterException", "InvalidImageFormatException", "ImageTooLargeException"}


@lru_cache
def _cliente():
    # Sin llaves en el .env, boto3 usa las credenciales del equipo o del rol.
    llaves = {}
    if configuracion.rekognition_access_key_id:
        llaves = {
            "aws_access_key_id": configuracion.rekognition_access_key_id,
            "aws_secret_access_key": configuracion.rekognition_secret_access_key,
        }
    return boto3.client("rekognition", region_name=configuracion.rekognition_region, **llaves)


def digito_verificador(cuerpo: str) -> str:
    # el mismo calculo que usa el Registro Civil.
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def buscar_run(texto: str) -> str | None:
    # El primer RUN con digito verificador correcto; asi se descartan lecturas erradas.
    for coincidencia in PATRON_RUN.finditer(texto):
        cuerpo = coincidencia.group(1).replace(".", "")
        verificador = coincidencia.group(2).upper()
        if digito_verificador(cuerpo) == verificador:
            return f"{cuerpo}-{verificador}"
    return None


def comparar_rostros(imagen_documento: bytes, imagen_rostro: bytes) -> Decimal:
    # Similitud entre la selfie y la foto de la cedula, de 0 a 100.
    try:
        respuesta = _cliente().compare_faces(
            SourceImage={"Bytes": imagen_rostro},
            TargetImage={"Bytes": imagen_documento},
            SimilarityThreshold=0,
        )
    except ClientError as error:
        # Sin rostro en alguna imagen: se rechaza, no es una falla del servicio.
        if error.response["Error"]["Code"] in ERRORES_DE_IMAGEN:
            return Decimal("0")
        raise ProveedorNoDisponible() from error
    except BotoCoreError as error:
        raise ProveedorNoDisponible() from error

    similitudes = [coincidencia["Similarity"] for coincidencia in respuesta.get("FaceMatches", [])]
    if not similitudes:
        return Decimal("0")
    return Decimal(str(max(similitudes))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def extraer_numero_documento(imagen_documento: bytes) -> str | None:
    # RUN leido del frente de la cedula, o None si no aparece uno valido.
    try:
        respuesta = _cliente().detect_text(Image={"Bytes": imagen_documento})
    except ClientError as error:
        if error.response["Error"]["Code"] in ERRORES_DE_IMAGEN:
            return None
        raise ProveedorNoDisponible() from error
    except BotoCoreError as error:
        raise ProveedorNoDisponible() from error

    # si el OCR lee "12.345.678 - 5" con espacios, la linea lo mantiene junto.
    lineas = [
        deteccion["DetectedText"]
        for deteccion in respuesta.get("TextDetections", [])
        if deteccion.get("Type") == "LINE"
    ]
    return buscar_run("\n".join(lineas))