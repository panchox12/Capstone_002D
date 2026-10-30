"""Pruebas de la conexion real con LiveKit, sin red.

Los permisos y la firma de los webhooks se calculan con las mismas llaves,
asi que se pueden comprobar localmente.
"""

import base64
import hashlib
import json

import jwt
import pytest
from livekit import api

from app.servicios.sala import EventoInvalido, SalaLiveKit, SalaNoConfigurada

LLAVE = "APIprueba"
SECRETO = "secreto-de-prueba-con-largo-suficiente-123"


@pytest.fixture()
def sala() -> SalaLiveKit:
    return SalaLiveKit("wss://cachai-prueba.livekit.cloud", LLAVE, SECRETO)


def _firmar(cuerpo: str) -> str:
    # Asi firma LiveKit sus webhooks: un JWT con el hash del cuerpo.
    resumen = base64.b64encode(hashlib.sha256(cuerpo.encode()).digest()).decode()
    return api.AccessToken(LLAVE, SECRETO).with_sha256(resumen).to_jwt()


def _aviso(evento: str, sala_nombre: str, identidad: str | None = None) -> str:
    datos = {"event": evento, "room": {"name": sala_nombre}}
    if identidad:
        datos["participant"] = {"identity": identidad}
    return json.dumps(datos)


def test_el_permiso_solo_sirve_para_esa_sala(sala) -> None:
    permiso = sala.crear_permiso("cachai-123", "usuario-1", "Valentina")

    datos = jwt.decode(permiso, SECRETO, algorithms=["HS256"], issuer=LLAVE)
    assert datos["sub"] == "usuario-1"
    assert datos["video"]["room"] == "cachai-123"
    assert datos["video"]["roomJoin"] is True


def test_lee_un_aviso_firmado_por_livekit(sala) -> None:
    cuerpo = _aviso("participant_joined", "cachai-123", "usuario-1")

    evento = sala.leer_evento(cuerpo, _firmar(cuerpo))

    assert (evento.tipo, evento.sala, evento.identidad) == ("participant_joined", "cachai-123", "usuario-1")


def test_rechaza_un_aviso_modificado(sala) -> None:
    original = _aviso("participant_joined", "cachai-123", "usuario-1")
    alterado = _aviso("participant_joined", "cachai-123", "usuario-2")

    with pytest.raises(EventoInvalido):
        sala.leer_evento(alterado, _firmar(original))


def test_rechaza_un_aviso_firmado_con_otras_llaves(sala) -> None:
    cuerpo = _aviso("room_finished", "cachai-123")
    resumen = base64.b64encode(hashlib.sha256(cuerpo.encode()).digest()).decode()
    falsa = api.AccessToken("otra", "otro-secreto-con-largo-suficiente-456").with_sha256(resumen).to_jwt()

    with pytest.raises(EventoInvalido):
        sala.leer_evento(cuerpo, falsa)


def test_sin_llaves_avisa_que_falta_configurar() -> None:
    with pytest.raises(SalaNoConfigurada):
        SalaLiveKit("", "", "").crear_permiso("cachai-123", "usuario-1", "Valentina")