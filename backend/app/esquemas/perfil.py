"""Esquemas del perfil publico."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.esquemas.habilidad import HabilidadLeer


class PerfilActualizar(BaseModel):
    biografia: str | None = Field(default=None, max_length=500)
    enlace_personalizado: str | None = Field(
        default=None, min_length=3, max_length=30, pattern=r"^[a-z0-9_-]+$"
    )


class PerfilPublicoLeer(BaseModel):
    usuario_id: uuid.UUID
    nombre_visible: str
    biografia: str | None
    enlace_personalizado: str | None
    url_perfil: str
    reputacion_promedio: Decimal
    total_evaluaciones: int
    consultas_completadas: int
    habilidades: list[HabilidadLeer]