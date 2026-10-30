"""Esquemas de validación y serialización para el buscador."""

import uuid
from pydantic import BaseModel, ConfigDict


class TutorEnBusqueda(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre_visible: str


class TemaEnBusqueda(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class ResultadoHabilidad(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    precio_por_bloque: int
    tema: TemaEnBusqueda
    usuario: TutorEnBusqueda