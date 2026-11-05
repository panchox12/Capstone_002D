"""Esquemas de valoraciones y bloqueos."""
 
import uuid
from datetime import datetime
 
from pydantic import BaseModel, Field
 
from app.modelos.moderacion import LARGO_MAXIMO_COMENTARIO
 
 
class ValoracionCrear(BaseModel):
    sesion_id: uuid.UUID
    estrellas: int = Field(ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=LARGO_MAXIMO_COMENTARIO)
 
 
class ValoracionLeer(BaseModel):
    sesion_id: uuid.UUID
    estrellas: int
    comentario: str | None
    creado_en: datetime
 
    model_config = {"from_attributes": True}
 
 
class EstadoValoracion(BaseModel):
    # Si ya valoraste esa sesion, con tu valoracion.
    valorada: bool
    valoracion: ValoracionLeer | None
 
 
class BloqueoCrear(BaseModel):
    usuario_id: uuid.UUID
 
 
class BloqueadoLeer(BaseModel):
    usuario_id: uuid.UUID
    nombre_visible: str
    desde: datetime