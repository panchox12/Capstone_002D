"""Esquemas de habilidades."""
 
import uuid
 
from pydantic import BaseModel, Field
 
from app.modelos.habilidad import EstadoHabilidad
 
 
class HabilidadCrear(BaseModel):
    tema_id: int
    precio_por_bloque: int = Field(gt=0)
 
 
class HabilidadActualizar(BaseModel):
    precio_por_bloque: int | None = Field(default=None, gt=0)
    estado: EstadoHabilidad | None = None
 
 
class HabilidadLeer(BaseModel):
    id: uuid.UUID
    tema_id: int
    tema_nombre: str
    precio_por_bloque: int
    estado: EstadoHabilidad