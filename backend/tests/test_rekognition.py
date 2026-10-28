"""Pruebas del proveedor Rekognition, sin llamar a AWS.

El cliente de boto3 se reemplaza por uno con respuestas preparadas (Stubber):
asi se prueba lo que hace Cachai con cada respuesta posible de AWS.
"""

import base64
from decimal import Decimal

import boto3
import pytest
from botocore.stub import ANY, Stubber
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.servicios import rekognition
from app.servicios import verificacion as servicio
from tests.utilidades import cabecera, crear_usuario

CEDULA = b"\xff\xd8\xff\xe0" + b"cedula"
SELFIE = b"\xff\xd8\xff\xe0" + b"selfie"


@pytest.fixture()
def aws(monkeypatch):
    # Cliente real de boto3, pero con respuestas preparadas y sin red.
    cliente = boto3.client(
        "rekognition", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x"
    )
    stubber = Stubber(cliente)
    monkeypatch.setattr(rekognition, "_cliente", lambda: cliente)
    monkeypatch.setattr(configuracion, "proveedor_identidad", "aws")
    with stubber:
        yield stubber
    stubber.assert_no_pending_responses()


def _lineas(*textos: str) -> dict:
    return {"TextDetections": [{"DetectedText": texto, "Type": "LINE"} for texto in textos]}


def _cuerpo() -> dict:
    return {
        "documento_frontal": base64.b64encode(CEDULA).decode(),
        "documento_reverso": base64.b64encode(CEDULA).decode(),
        "rostro": base64.b64encode(SELFIE).decode(),
        "consentimiento_biometrico": True,
    }


# --- RUN ----------------------------------------------------------------------


def test_el_digito_verificador_se_calcula_con_modulo_11() -> None:
    assert rekognition.digito_verificador("12345678") == "5"
    assert rekognition.digito_verificador("11111111") == "1"
    assert rekognition.digito_verificador("10000013") == "K"


def test_busca_el_run_con_o_sin_puntos() -> None:
    assert rekognition.buscar_run("RUN 12.345.678-5") == "12345678-5"
    assert rekognition.buscar_run("RUN 12345678-5") == "12345678-5"


def test_descarta_un_run_con_digito_verificador_incorrecto() -> None:
    assert rekognition.buscar_run("RUN 12.345.678-9") is None


def test_extrae_el_run_de_las_lineas_de_la_cedula(aws) -> None:
    aws.add_response(
        "detect_text", _lineas("CEDULA DE IDENTIDAD", "RUN 12.345.678-5"), {"Image": {"Bytes": CEDULA}}
    )

    assert rekognition.extraer_numero_documento(CEDULA) == "12345678-5"


def test_sin_run_legible_devuelve_none(aws) -> None:
    aws.add_response("detect_text", _lineas("CHILE", "CEDULA DE IDENTIDAD"), {"Image": {"Bytes": CEDULA}})

    assert rekognition.extraer_numero_documento(CEDULA) is None


# --- Rostros ------------------------------------------------------------------


def test_devuelve_la_mayor_similitud_redondeada(aws) -> None:
    aws.add_response(
        "compare_faces",
        {"FaceMatches": [{"Similarity": 97.4567}, {"Similarity": 88.0}], "UnmatchedFaces": []},
        {"SourceImage": {"Bytes": SELFIE}, "TargetImage": {"Bytes": CEDULA}, "SimilarityThreshold": ANY},
    )

    assert rekognition.comparar_rostros(CEDULA, SELFIE) == Decimal("97.46")


def test_sin_coincidencias_la_similitud_es_cero(aws) -> None:
    aws.add_response("compare_faces", {"FaceMatches": [], "UnmatchedFaces": [{}]})

    assert rekognition.comparar_rostros(CEDULA, SELFIE) == Decimal("0")


def test_una_selfie_sin_rostro_se_rechaza_sin_caerse(aws) -> None:
    aws.add_client_error("compare_faces", service_error_code="InvalidParameterException")

    assert rekognition.comparar_rostros(CEDULA, SELFIE) == Decimal("0")


def test_si_aws_falla_avisa_que_el_proveedor_no_esta_disponible(aws) -> None:
    aws.add_client_error("compare_faces", service_error_code="ThrottlingException")

    with pytest.raises(servicio.ProveedorNoDisponible):
        rekognition.comparar_rostros(CEDULA, SELFIE)


# --- Flujo completo con el proveedor aws ---------------------------------------


def test_la_verificacion_con_aws_aprueba_al_usuario(db_prueba: Session, cliente_db: TestClient, aws) -> None:
    usuario = crear_usuario(db_prueba)
    aws.add_response("detect_text", _lineas("RUN 12.345.678-5"))
    aws.add_response("compare_faces", {"FaceMatches": [{"Similarity": 99.1}]})

    respuesta = cliente_db.post("/verificacion", headers=cabecera(usuario), json=_cuerpo())

    assert respuesta.status_code == 201
    assert respuesta.json()["resultado"] == "aprobado"
    assert servicio.esta_verificado(db_prueba, usuario.id)


def test_con_aws_caido_la_api_responde_503(db_prueba: Session, cliente_db: TestClient, aws) -> None:
    usuario = crear_usuario(db_prueba)
    aws.add_client_error("detect_text", service_error_code="ServiceUnavailableException", http_status_code=503)

    respuesta = cliente_db.post("/verificacion", headers=cabecera(usuario), json=_cuerpo())

    assert respuesta.status_code == 503