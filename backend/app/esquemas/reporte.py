"""Esquemas de los reportes y de su revision por soporte."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.esquemas.solicitud import Participante
from app.modelos.moderacion import LARGO_MAXIMO_DESCRIPCION, EstadoReporte, MotivoReporte, TipoSancion
from app.modelos.sesion import EstadoSesion

DIAS_MAXIMOS_SUSPENSION = 365


class ReporteCrear(BaseModel):
    sesion_id: uuid.UUID
    motivo: MotivoReporte
    descripcion: str = Field(min_length=10, max_length=LARGO_MAXIMO_DESCRIPCION)


class ReporteLeer(BaseModel):
    id: uuid.UUID
    folio: int
    sesion_id: uuid.UUID
    motivo: MotivoReporte
    descripcion: str
    estado: EstadoReporte
    congela_pago: bool
    resolucion: str | None
    fecha_resolucion: datetime | None
    creado_en: datetime

    model_config = {"from_attributes": True}


class ReporteResumen(BaseModel):
    # Una fila de la bandeja de soporte.
    id: uuid.UUID
    folio: int
    motivo: MotivoReporte
    estado: EstadoReporte
    congela_pago: bool
    tema_nombre: str
    reportante: Participante
    reportado: Participante
    creado_en: datetime


class PagoSesion(BaseModel):
    retenido: int
    pagado: int
    devuelto: int


class ReporteDetalle(ReporteResumen):
    descripcion: str
    resolucion: str | None
    fecha_resolucion: datetime | None
    sesion_id: uuid.UUID
    estado_sesion: EstadoSesion
    precio_bloque: int
    bloques_cobrados: int
    fecha_conexion_ambos: datetime | None
    fecha_cierre: datetime | None
    motivo_cierre: str | None
    pago: PagoSesion
    sanciones_previas_reportado: int
    # grabando, disponible, fallida, borrada; vacio si la sesion no se grabo.
    grabacion: str | None


class EnlaceGrabacion(BaseModel):
    url: str
    segundos_vigencia: int


class AccesoLeer(BaseModel):
    soporte: str
    fecha: datetime


class Resolucion(BaseModel):
    fundado: bool
    resolucion: str = Field(min_length=10, max_length=LARGO_MAXIMO_DESCRIPCION)
    tipo_sancion: TipoSancion | None = None
    dias_suspension: int | None = Field(default=None, ge=1, le=DIAS_MAXIMOS_SUSPENSION)

    # La suspension temporal necesita los dias; la definitiva no los lleva.
    @model_validator(mode="after")
    def dias_segun_sancion(self):
        if self.tipo_sancion == TipoSancion.TEMPORAL and self.dias_suspension is None:
            raise ValueError("Indica cuantos dias dura la suspension")
        if self.tipo_sancion != TipoSancion.TEMPORAL and self.dias_suspension is not None:
            raise ValueError("Los dias solo se indican en una suspension temporal")
        return self