"""Esquemas de los avisos de la campana."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificacionLeer(BaseModel):
    id: uuid.UUID
    tipo: str
    titulo: str
    mensaje: str
    enlace: str | None
    leida: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


class Bandeja(BaseModel):
    no_leidas: int
    avisos: list[NotificacionLeer]