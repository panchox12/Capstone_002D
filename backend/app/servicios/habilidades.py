"""Publicacion y edicion de habilidades.
 
Estas funciones no confirman: el endpoint que las llama
decide cuando se confirma la operacion completa.
"""
 
import uuid
 
from sqlalchemy import select
from sqlalchemy.orm import Session
 
from app.modelos.habilidad import EstadoHabilidad, HabilidadOfrecida
from app.modelos.tema import NIVEL_MAXIMO, EstadoTema, Tema
from app.servicios import parametros
 
PARAM_PRECIO_MAXIMO = "precio_maximo_bloque"
 
 
class TemaNoOfrecible(Exception):
    """Solo se ofrecen temas activos del ultimo nivel del catalogo."""
 
 
class PrecioInvalido(Exception):
    """El precio es cero, negativo, o supera el maximo activo."""
 
 
class HabilidadDuplicada(Exception):
    """El usuario ya ofrece ese tema."""
 
 
class HabilidadNoEncontrada(Exception):
    """No existe, o pertenece a otro usuario."""
 
 
def validar_precio(db: Session, precio: int) -> None:
    """Seccion 3.6: mayor que cero, y bajo el maximo si el maximo esta activo.
 
    Un maximo de 0 significa que el limite esta desactivado.
    """
    if precio <= 0:
        raise PrecioInvalido("El precio debe ser mayor que cero")
    maximo = parametros.obtener_entero(db, PARAM_PRECIO_MAXIMO)
    if maximo > 0 and precio > maximo:
        raise PrecioInvalido(f"El precio maximo por bloque es {maximo} tokens")
 
 
def publicar(db: Session, usuario_id: uuid.UUID, tema_id: int, precio: int) -> HabilidadOfrecida:
    tema = db.get(Tema, tema_id)
    if tema is None or tema.nivel != NIVEL_MAXIMO or tema.estado != EstadoTema.ACTIVO:
        raise TemaNoOfrecible()
 
    validar_precio(db, precio)
 
    existente = db.execute(
        select(HabilidadOfrecida).where(
            HabilidadOfrecida.usuario_id == usuario_id,
            HabilidadOfrecida.tema_id == tema_id,
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise HabilidadDuplicada()
 
    habilidad = HabilidadOfrecida(usuario_id=usuario_id, tema_id=tema_id, precio_por_bloque=precio)
    db.add(habilidad)
    db.flush()
    return habilidad
 
 
def actualizar(
    db: Session,
    usuario_id: uuid.UUID,
    habilidad_id: uuid.UUID,
    precio: int | None = None,
    estado: EstadoHabilidad | None = None,
) -> HabilidadOfrecida:
    """Cambia el precio o el estado. Solo el dueno puede hacerlo."""
    habilidad = db.get(HabilidadOfrecida, habilidad_id)
    # Si es de otro usuario se responde igual que si no existiera, para no
    # revelar que ese id existe.
    if habilidad is None or habilidad.usuario_id != usuario_id:
        raise HabilidadNoEncontrada()
 
    if precio is not None:
        validar_precio(db, precio)
        habilidad.precio_por_bloque = precio
    if estado is not None:
        habilidad.estado = estado
 
    db.flush()
    return habilidad
 
 
def listar(
    db: Session,
    usuario_id: uuid.UUID,
    solo_publicadas: bool = False,
) -> list[tuple[HabilidadOfrecida, Tema]]:
    """Las habilidades de un usuario junto con su tema, ordenadas por nombre."""
    sentencia = (
        select(HabilidadOfrecida, Tema)
        .join(Tema, Tema.id == HabilidadOfrecida.tema_id)
        .where(HabilidadOfrecida.usuario_id == usuario_id)
        .order_by(Tema.nombre)
    )
    if solo_publicadas:
        sentencia = sentencia.where(HabilidadOfrecida.estado == EstadoHabilidad.PUBLICADA)
    return [(fila[0], fila[1]) for fila in db.execute(sentencia).all()]