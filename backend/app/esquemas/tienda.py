"""Esquemas de la tienda."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modelos.compra import EstadoCompra


class PaqueteLeer(BaseModel):
    codigo: str
    cantidad_tokens: int
    monto_pesos: int
    pesos_por_token: int


class CompraCrear(BaseModel):
    paquete: str = Field(min_length=1, max_length=20)


class CompraLeer(BaseModel):
    id: uuid.UUID
    paquete: str
    cantidad_tokens: int
    monto_pesos: int
    estado: EstadoCompra
    fecha: datetime
    fecha_vencimiento: datetime | None
    tokens_restantes: int
    vencida: bool
