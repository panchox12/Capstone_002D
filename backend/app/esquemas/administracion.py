"""Esquemas del panel del administrador."""
 
from datetime import datetime
 
from pydantic import BaseModel, Field
 
 
class ParametroLeer(BaseModel):
    nombre: str
    valor: str
    descripcion: str | None
    actualizado_en: datetime
 
    model_config = {"from_attributes": True}
 
 
class ParametroCambiar(BaseModel):
    valor: int = Field(ge=0, le=100_000)
 
 
class Indicadores(BaseModel):
    dias_ventana: int
    masa_circulante: int
    tokens_retenidos: int
    tokens_entregados: int
    tokens_consumidos: int
    tokens_vencidos: int
    velocidad: float
    tasa_caducidad: float
    cobertura_gratuita: float
    conversion: float
    usuarios_activos: int
    sesiones_terminadas: int