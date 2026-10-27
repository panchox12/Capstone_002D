"""Esquemas de las solicitudes de sesion."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modelos.solicitud import LARGO_MAXIMO_MENSAJE, EstadoSolicitud, ModalidadSolicitud


class SolicitudCrear(BaseModel):
    habilidad_id: uuid.UUID
    mensaje: str = Field(min_length=1, max_length=LARGO_MAXIMO_MENSAJE)

    # Un mensaje de puros espacios no cuenta.
    @field_validator("mensaje")
    @classmethod
    def no_vacio(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("Cuentale tu duda en el mensaje")
        return valor


class Participante(BaseModel):
    id: uuid.UUID
    nombre_visible: str


class SolicitudLeer(BaseModel):
    id: uuid.UUID
    estado: EstadoSolicitud
    modalidad: ModalidadSolicitud
    mensaje: str
    precio_bloque: int
    tema_nombre: str
    aprendiz: Participante
    tutor: Participante
    fecha_envio: datetime
    fecha_limite_respuesta: datetime
    fecha_resolucion: datetime | None
    # Lo calcula el servidor; el navegador solo lo muestra.
    segundos_restantes: int