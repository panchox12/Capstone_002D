"""Valoraciones de 1 a 5 estrellas al terminar una sesion.
 
Cada participante puede valorar al otro una vez, si quiere. El promedio del
perfil se actualiza al momento; el buscador y el perfil lo muestran recien
desde el minimo de valoraciones del parametro.
Ninguna funcion hace commit: quien la llama confirma todo junto, o nada.
"""
 
import uuid
from decimal import ROUND_HALF_UP, Decimal
 
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
 
from app.modelos.moderacion import Valoracion
from app.modelos.sesion import EstadoSesion, Sesion
from app.modelos.solicitud import Solicitud
from app.servicios import perfiles
 
 
class SesionNoValorable(Exception):
    # No existe, no participaste, o la llamada nunca empezo.
    pass
 
 
class ValoracionDuplicada(Exception):
    pass
 
 
def _sesion_propia(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> tuple[Sesion, Solicitud]:
    fila = db.execute(
        select(Sesion, Solicitud)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .where(Sesion.id == sesion_id, or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id))
    ).first()
    if fila is None:
        raise SesionNoValorable()
    return fila[0], fila[1]
 
 
def valorar(
    db: Session, evaluador_id: uuid.UUID, sesion_id: uuid.UUID, estrellas: int, comentario: str | None
) -> Valoracion:
    sesion, solicitud = _sesion_propia(db, evaluador_id, sesion_id)
    # Solo se valora una llamada que de verdad ocurrio.
    if sesion.estado != EstadoSesion.TERMINADA or sesion.fecha_conexion_ambos is None:
        raise SesionNoValorable()
    if de_sesion(db, evaluador_id, sesion_id) is not None:
        raise ValoracionDuplicada()
 
    evaluado_id = solicitud.tutor_id if evaluador_id == solicitud.aprendiz_id else solicitud.aprendiz_id
    valoracion = Valoracion(
        sesion_id=sesion.id,
        evaluador_id=evaluador_id,
        evaluado_id=evaluado_id,
        estrellas=estrellas,
        comentario=(comentario or "").strip() or None,
    )
    db.add(valoracion)
 
    # Promedio acumulado: no hace falta recorrer todas las valoraciones anteriores.
    perfil = perfiles.obtener_o_crear(db, evaluado_id)
    total = perfil.total_evaluaciones + 1
    suma = perfil.reputacion_promedio * perfil.total_evaluaciones + estrellas
    perfil.reputacion_promedio = (suma / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    perfil.total_evaluaciones = total
    db.flush()
    return valoracion
 
 
def de_sesion(db: Session, evaluador_id: uuid.UUID, sesion_id: uuid.UUID) -> Valoracion | None:
    return db.execute(
        select(Valoracion).where(Valoracion.sesion_id == sesion_id, Valoracion.evaluador_id == evaluador_id)
    ).scalar_one_or_none()