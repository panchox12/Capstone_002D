"""Esquemas de las sesiones de videollamada."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.esquemas.solicitud import Participante
from app.modelos.sesion import EstadoSesion


class SesionLeer(BaseModel):
    id: uuid.UUID
    solicitud_id: uuid.UUID
    estado: EstadoSesion
    tema_nombre: str
    precio_bloque: int
    aprendiz: Participante
    tutor: Participante
    fecha_apertura_sala: datetime
    fecha_limite_conexion: datetime
    fecha_conexion_ambos: datetime | None
    fecha_cierre: datetime | None
    bloques_cobrados: int
    motivo_cierre: str | None
    # Los calcula el servidor; el navegador solo los muestra.
    segundos_para_conectarse: int
    # Tiempo pagado que queda, contando las extensiones. Con alguien caido no avanza.
    segundos_restantes_bloque: int
    # Extension pendiente: quien la propuso. Vacio si no hay ninguna.
    extension_propuesta_por: uuid.UUID | None
    # Pausa por caida de conexion.
    pausa_activa: bool
    usuario_caido_id: uuid.UUID | None
    segundos_para_reconectar: int
    pausas_usadas: int
    pausas_maximas: int


class PermisoSala(BaseModel):
    url: str
    token: str
    nombre_sala: str