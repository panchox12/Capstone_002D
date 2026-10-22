"""Entradas de tokens gratuitos: la entrega semanal y los videos publicitarios.

El saldo gratuito tiene un tope. La entrega semanal rellena hasta el tope,
no suma encima, y un video solo entrega tokens si el saldo gratuito esta
bajo el tope.
"""

import uuid
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modelos.lote_tokens import EstadoLote, LoteDeTokens, OrigenLote, TipoSaldo
from app.modelos.usuario import EstadoCuenta, Usuario
from app.modelos.video_visto import VideoVisto
from app.servicios import parametros, tokens

PARAM_TOKENS_SEMANALES = "tokens_gratis_semanales"
PARAM_TOPE_GRATIS = "tope_saldo_gratis"
PARAM_TOKENS_POR_VIDEO = "tokens_por_video"
PARAM_TOPE_VIDEOS = "tope_videos_por_dia"


class TopeDeVideos(Exception):
    """El usuario ya vio todos los videos permitidos en las ultimas 24 horas."""


class SaldoGratisCompleto(Exception):
    """El saldo gratuito ya esta en el tope"""

#Si llegan dos entradas a la vez para el mismo usuario, la segunda espera
#a que la primera termine y ve el saldo ya actualizado.
def _bloquear_usuario(db: Session, usuario_id: uuid.UUID) -> None:
    db.execute(select(Usuario.id).where(Usuario.id == usuario_id).with_for_update())

#Cuantos tokens gratuitos le faltan al usuario para llegar al tope.
def espacio_gratis(db: Session, usuario_id: uuid.UUID) -> int:
    tope = parametros.obtener_entero(db, PARAM_TOPE_GRATIS)
    actual = tokens.calcular_saldo(db, usuario_id, TipoSaldo.GRATIS)
    return max(0, tope - actual)

#Rellena el saldo gratuito hasta el tope. Devuelve cuantos tokens entrego.
def entregar_semanal(db: Session, usuario_id: uuid.UUID) -> int:
    _bloquear_usuario(db, usuario_id)
    semanales = parametros.obtener_entero(db, PARAM_TOKENS_SEMANALES)
    cantidad = min(semanales, espacio_gratis(db, usuario_id))
    if cantidad <= 0:
        return 0

    tokens.otorgar(
        db,
        usuario_id=usuario_id,
        cantidad=cantidad,
        tipo_saldo=TipoSaldo.GRATIS,
        origen=OrigenLote.ENTREGA_SEMANAL,
        dias_vigencia=tokens.dias_de_vigencia(db, OrigenLote.ENTREGA_SEMANAL),
    )
    return cantidad

#La entrega de los lunes. Devuelve a cuantos usuarios les llego algo.
def entregar_semanal_a_todos(db: Session) -> int:
    activos = db.execute(
        select(Usuario.id).where(Usuario.estado_cuenta == EstadoCuenta.ACTIVA)
    ).scalars().all()
    return sum(1 for usuario_id in activos if entregar_semanal(db, usuario_id) > 0)

def videos_vistos_hoy(db: Session, usuario_id: uuid.UUID) -> int:
    #Videos de las ultimas 24 horas, contadas hacia atras desde ahora.
    desde = tokens.ahora() - timedelta(hours=24)
    sentencia = select(func.count()).select_from(VideoVisto).where(
        VideoVisto.usuario_id == usuario_id,
        VideoVisto.fecha > desde,
    )
    return int(db.execute(sentencia).scalar_one())


def ver_video(db: Session, usuario_id: uuid.UUID) -> VideoVisto:
    #Entrega los tokens de un video visto, respetando el tope diario y el tope de saldo.
    _bloquear_usuario(db, usuario_id)

    if videos_vistos_hoy(db, usuario_id) >= parametros.obtener_entero(db, PARAM_TOPE_VIDEOS):
        raise TopeDeVideos()

    por_video = parametros.obtener_entero(db, PARAM_TOKENS_POR_VIDEO)
    cantidad = min(por_video, espacio_gratis(db, usuario_id))
    if cantidad <= 0:
        raise SaldoGratisCompleto()

    lote = tokens.otorgar(
        db,
        usuario_id=usuario_id,
        cantidad=cantidad,
        tipo_saldo=TipoSaldo.GRATIS,
        origen=OrigenLote.VIDEO,
        dias_vigencia=tokens.dias_de_vigencia(db, OrigenLote.VIDEO),
    )
    video = VideoVisto(
        usuario_id=usuario_id,
        fecha=lote.fecha_recepcion,
        tokens_otorgados=cantidad,
        lote_id=lote.id,
    )
    db.add(video)
    db.flush()
    return video

def vencer_lotes(db: Session) -> int:
    #Marca como vencidos los lotes cuya fecha ya paso. Devuelve cuantos marco.
    #Cambia la etiqueta a VENCIDO en la db.
    resultado = db.execute(
        update(LoteDeTokens)
        .where(
            LoteDeTokens.estado == EstadoLote.VIGENTE,
            LoteDeTokens.fecha_vencimiento <= tokens.ahora(),
        )
        .values(estado=EstadoLote.VENCIDO)
    )
    return resultado.rowcount
