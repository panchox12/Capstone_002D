"""Esquemas del catalogo de temas."""
 
from pydantic import BaseModel
 
 
class TemaNodo(BaseModel):
    """Un tema con sus hijos. Se define a si mismo porque el arbol es recursivo."""
 
    id: int
    nombre: str
    nivel: int
    descripcion: str | None = None
    hijos: list["TemaNodo"] = []
 
 
TemaNodo.model_rebuild()