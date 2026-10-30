"""Esquemas del buscador."""

import uuid

from pydantic import BaseModel

from app.servicios.buscador import Modo


class ResultadoBusqueda(BaseModel):
    habilidad_id: uuid.UUID
    tema_id: int
    tema_nombre: str
    ruta: str
    puntaje: float
    precio_por_bloque: int
    tutor_id: uuid.UUID
    tutor_nombre: str
    # Nulo mientras el tutor no tenga el minimo de valoraciones.
    reputacion_promedio: float | None
    total_evaluaciones: int
    en_linea: bool


class RespuestaBusqueda(BaseModel):
    # El modo que se uso de verdad: si no hay vectores, el semantico pasa a lexico.
    modo: Modo
    resultados: list[ResultadoBusqueda]