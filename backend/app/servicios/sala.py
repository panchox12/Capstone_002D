"""Conexion con LiveKit.

Cachai no transmite video: le pide a LiveKit un permiso para que cada
participante entre a la sala, y LiveKit le avisa a Cachai (webhook) cuando
alguien entra o sale. Con esos avisos el servidor lleva la cuenta del tiempo.
"""

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from livekit import api

from app.core.config import configuracion

# El permiso para entrar dura poco: solo sirve para conectarse.
VIGENCIA_PERMISO = timedelta(hours=2)


class SalaNoConfigurada(Exception):
    # Faltan LIVEKIT_URL, LIVEKIT_API_KEY o LIVEKIT_API_SECRET en el .env.
    pass


class EventoInvalido(Exception):
    # El aviso no viene firmado por LiveKit con nuestras llaves.
    pass


@dataclass(frozen=True)
class EventoSala:
    tipo: str
    sala: str
    identidad: str | None


class SalaLiveKit:
    def __init__(self, url: str, llave: str, secreto: str):
        self.url = url
        self.llave = llave
        self.secreto = secreto

    def _exigir_configuracion(self) -> None:
        if not (self.url and self.llave and self.secreto):
            raise SalaNoConfigurada()

    def crear_permiso(self, nombre_sala: str, identidad: str, nombre: str) -> str:
        # Token firmado que deja entrar a esa sala y a ninguna otra.
        self._exigir_configuracion()
        return (
            api.AccessToken(self.llave, self.secreto)
            .with_identity(identidad)
            .with_name(nombre)
            .with_grants(api.VideoGrants(room_join=True, room=nombre_sala))
            .with_ttl(VIGENCIA_PERMISO)
            .to_jwt()
        )

    def leer_evento(self, cuerpo: str, autorizacion: str) -> EventoSala:
        # Comprueba la firma del webhook y devuelve lo que paso.
        self._exigir_configuracion()
        token = autorizacion.removeprefix("Bearer ").strip()
        receptor = api.WebhookReceiver(api.TokenVerifier(self.llave, self.secreto))
        try:
            evento = receptor.receive(cuerpo, token)
        except Exception as error:
            raise EventoInvalido() from error
        return EventoSala(
            tipo=evento.event,
            sala=evento.room.name,
            identidad=evento.participant.identity or None,
        )

    def cerrar(self, nombre_sala: str) -> None:
        # Saca a todos de la sala. Lo usa el planificador al terminar o cancelar una sesion.
        self._exigir_configuracion()

        async def _borrar() -> None:
            async with api.LiveKitAPI(self.url, self.llave, self.secreto) as cliente:
                await cliente.room.delete_room(api.DeleteRoomRequest(room=nombre_sala))

        asyncio.run(_borrar())


def obtener_sala() -> SalaLiveKit:
    # Dependencia de FastAPI. Las pruebas la reemplazan por una sala falsa.
    return SalaLiveKit(configuracion.livekit_url, configuracion.livekit_api_key, configuracion.livekit_api_secret)