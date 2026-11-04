"""Sesiones: abrir la sala, contar el tiempo con los avisos de LiveKit y pagar.

Reglas que este modulo garantiza:
- El bloque 1 empieza cuando los dos estan conectados, con la hora del servidor.
- Si no se conectan los dos a tiempo, la sesion se cancela y el aprendiz recupera sus tokens.
- Una extension la propone uno y la acepta el otro; el aprendiz paga el bloque nuevo.
- Si alguien se cae, el reloj se detiene hasta 90 segundos. Si no vuelve, o se cae por cuarta
  vez, la sesion termina y no paga quien mantuvo la conexion.
- El bloque empezado se cobra completo aunque la sesion termine antes; el que no alcanzo a
  empezar se devuelve.
- El tutor recibe el pago unos minutos despues del cierre, para dar tiempo a reportar.
Ninguna funcion hace commit: quien la llama confirma todo junto, o nada.
"""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modelos.habilidad import HabilidadOfrecida
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.sesion import (
    Bloque,
    EstadoBloque,
    EstadoPausa,
    EstadoSesion,
    EventoConexion,
    PausaSesion,
    Sesion,
    TipoEventoConexion,
)
from app.modelos.solicitud import Solicitud
from app.modelos.tema import Tema
from app.modelos.usuario import Usuario
from app.servicios import parametros, tokens
from app.servicios.sala import EventoSala, SalaLiveKit

PARAM_VENTANA_CONEXION = "ventana_conexion_sala_minutos"
PARAM_DURACION_BLOQUE = "duracion_bloque_minutos"
PARAM_RETENCION_POSTERIOR = "retencion_posterior_sesion_minutos"
PARAM_RECONEXION = "tiempo_reconexion_segundos"
PARAM_PAUSAS_MAXIMAS = "pausas_maximas_por_sesion"

registro = logging.getLogger("uvicorn.error")


class SesionNoEncontrada(Exception):
    # No existe, o el usuario no participa en ella.
    pass


class SalaCerrada(Exception):
    # La sesion ya termino o se cancelo: no se puede entrar.
    pass


class SesionNoEnCurso(Exception):
    # La accion solo tiene sentido mientras la llamada esta corriendo.
    pass


class ExtensionYaPropuesta(Exception):
    pass


class SinExtensionPendiente(Exception):
    pass


class ExtensionPropia(Exception):
    # Quien propone la extension no la acepta: la acepta el otro.
    pass


# ---------------------------------------------------------------------------
# Abrir
# ---------------------------------------------------------------------------


def _retencion_de_solicitud(db: Session, solicitud_id: uuid.UUID) -> Retencion:
    return db.execute(select(Retencion).where(Retencion.solicitud_id == solicitud_id)).scalar_one()


def abrir(db: Session, solicitud: Solicitud) -> Sesion:
    # La llama solicitudes.aceptar(), cuando la retencion del primer bloque ya existe.
    momento = tokens.ahora()
    minutos = parametros.obtener_entero(db, PARAM_VENTANA_CONEXION)
    sesion_id = uuid.uuid4()
    sesion = Sesion(
        id=sesion_id,
        solicitud_id=solicitud.id,
        nombre_sala=f"cachai-{sesion_id}",
        estado=EstadoSesion.ESPERANDO,
        fecha_apertura_sala=momento,
        fecha_limite_conexion=momento + timedelta(minutes=minutos),
        bloques_cobrados=0,
    )
    db.add(sesion)
    db.flush()

    # Desde ahora los tokens retenidos pertenecen a la sesion.
    _retencion_de_solicitud(db, solicitud.id).sesion_id = sesion.id
    db.flush()
    return sesion


# ---------------------------------------------------------------------------
# Entrar a la sala
# ---------------------------------------------------------------------------


def _sesion_y_solicitud(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> tuple[Sesion, Solicitud]:
    fila = db.execute(
        select(Sesion, Solicitud)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .where(
            Sesion.id == sesion_id,
            or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id),
        )
    ).first()
    if fila is None:
        raise SesionNoEncontrada()
    return fila[0], fila[1]


def entrar(db: Session, sala: SalaLiveKit, usuario: Usuario, sesion_id: uuid.UUID) -> tuple[Sesion, str]:
    # Devuelve la sesion y el permiso de LiveKit para que el usuario entre.
    sesion, _ = _sesion_y_solicitud(db, usuario.id, sesion_id)
    if sesion.estado not in (EstadoSesion.ESPERANDO, EstadoSesion.EN_CURSO):
        raise SalaCerrada()
    permiso = sala.crear_permiso(sesion.nombre_sala, str(usuario.id), usuario.nombre_visible)
    return sesion, permiso


# ---------------------------------------------------------------------------
# Avisos de LiveKit
# ---------------------------------------------------------------------------

TIPOS_DE_CONEXION = {
    "participant_joined": TipoEventoConexion.ENTRO,
    "participant_left": TipoEventoConexion.SALIO,
}


def _ambos_presentes(db: Session, sesion: Sesion, solicitud: Solicitud) -> bool:
    # Esta presente quien ha entrado mas veces de las que ha salido.
    for usuario_id in (solicitud.aprendiz_id, solicitud.tutor_id):
        entradas = db.scalar(
            select(func.count()).where(
                EventoConexion.sesion_id == sesion.id,
                EventoConexion.usuario_id == usuario_id,
                EventoConexion.tipo_evento == TipoEventoConexion.ENTRO,
            )
        )
        salidas = db.scalar(
            select(func.count()).where(
                EventoConexion.sesion_id == sesion.id,
                EventoConexion.usuario_id == usuario_id,
                EventoConexion.tipo_evento == TipoEventoConexion.SALIO,
            )
        )
        if entradas <= salidas:
            return False
    return True


def _iniciar(db: Session, sesion: Sesion, solicitud: Solicitud) -> None:
    # El primer bloque ya esta pagado: es la retencion de la solicitud.
    momento = tokens.ahora()
    minutos = parametros.obtener_entero(db, PARAM_DURACION_BLOQUE)
    sesion.estado = EstadoSesion.EN_CURSO
    sesion.fecha_conexion_ambos = momento
    sesion.bloques_cobrados = 1
    db.add(
        Bloque(
            sesion_id=sesion.id,
            numero_orden=1,
            hora_inicio=momento,
            hora_termino=momento + timedelta(minutes=minutos),
            tokens_cobrados=solicitud.precio_bloque,
            retencion_id=_retencion_de_solicitud(db, solicitud.id).id,
            estado=EstadoBloque.EN_CURSO,
        )
    )
    db.flush()


def registrar_evento(db: Session, evento: EventoSala) -> None:
    # Procesa un aviso de LiveKit. Los avisos de salas ajenas se ignoran.
    sesion = db.execute(
        select(Sesion).where(Sesion.nombre_sala == evento.sala).with_for_update()
    ).scalar_one_or_none()
    if sesion is None or sesion.estado not in (EstadoSesion.ESPERANDO, EstadoSesion.EN_CURSO):
        return

    if evento.tipo == "room_finished":
        if sesion.estado == EstadoSesion.EN_CURSO:
            terminar(db, sesion, "la sala se cerro")
        return

    tipo = TIPOS_DE_CONEXION.get(evento.tipo)
    if tipo is None or evento.identidad is None:
        return
    try:
        usuario_id = uuid.UUID(evento.identidad)
    except ValueError:
        return
    solicitud = db.get(Solicitud, sesion.solicitud_id)
    if usuario_id not in (solicitud.aprendiz_id, solicitud.tutor_id):
        return

    db.add(
        EventoConexion(
            sesion_id=sesion.id,
            usuario_id=usuario_id,
            tipo_evento=tipo,
            marca_temporal=tokens.ahora(),
        )
    )
    db.flush()

    # Con la llamada corriendo, salir abre una pausa y volver la cierra.
    if sesion.estado == EstadoSesion.EN_CURSO:
        if tipo == TipoEventoConexion.SALIO:
            _abrir_pausa(db, sesion, solicitud, usuario_id)
        else:
            pausa = pausa_abierta(db, sesion.id, usuario_id)
            if pausa is not None:
                _cerrar_pausa(db, sesion, pausa)
        return

    # Si alguien llega despues del plazo, el planificador cancela la sesion.
    a_tiempo = tokens.ahora() < sesion.fecha_limite_conexion
    if tipo == TipoEventoConexion.ENTRO and a_tiempo and _ambos_presentes(db, sesion, solicitud):
        _iniciar(db, sesion, solicitud)


# ---------------------------------------------------------------------------
# Pausas por caida de conexion
# ---------------------------------------------------------------------------


def pausa_abierta(db: Session, sesion_id: uuid.UUID, usuario_id: uuid.UUID | None = None) -> PausaSesion | None:
    sentencia = select(PausaSesion).where(
        PausaSesion.sesion_id == sesion_id, PausaSesion.estado == EstadoPausa.ABIERTA
    )
    if usuario_id is not None:
        sentencia = sentencia.where(PausaSesion.usuario_id == usuario_id)
    return db.execute(sentencia.order_by(PausaSesion.inicio).limit(1)).scalar_one_or_none()


def contar_pausas(db: Session, sesion_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).where(PausaSesion.sesion_id == sesion_id))


def _abrir_pausa(db: Session, sesion: Sesion, solicitud: Solicitud, usuario_id: uuid.UUID) -> None:
    if pausa_abierta(db, sesion.id, usuario_id) is not None:
        return
    # Pasado el maximo de pausas, la siguiente caida termina la sesion.
    if contar_pausas(db, sesion.id) >= parametros.obtener_entero(db, PARAM_PAUSAS_MAXIMAS):
        _cerrar_por_caida(db, sesion, solicitud, usuario_id, "se acabaron las pausas por caidas de conexion")
        return
    momento = tokens.ahora()
    segundos = parametros.obtener_entero(db, PARAM_RECONEXION)
    db.add(
        PausaSesion(
            sesion_id=sesion.id,
            usuario_id=usuario_id,
            inicio=momento,
            limite_reconexion=momento + timedelta(seconds=segundos),
            estado=EstadoPausa.ABIERTA,
        )
    )
    db.flush()


def _inicio_del_corte(db: Session, pausa: PausaSesion) -> datetime:
    # Si las caidas se encimaron, el reloj estuvo detenido desde la primera.
    inicio = pausa.inicio
    otras = db.execute(
        select(PausaSesion).where(
            PausaSesion.sesion_id == pausa.sesion_id,
            PausaSesion.id != pausa.id,
            PausaSesion.estado == EstadoPausa.RECONECTADA,
        )
    ).scalars().all()
    cambio = True
    while cambio:
        cambio = False
        for otra in otras:
            if otra.inicio < inicio and otra.fin is not None and otra.fin >= inicio:
                inicio = otra.inicio
                cambio = True
    return inicio


def _cerrar_pausa(db: Session, sesion: Sesion, pausa: PausaSesion) -> None:
    momento = tokens.ahora()
    pausa.fin = momento
    pausa.estado = EstadoPausa.RECONECTADA
    db.flush()
    # Mientras alguien siga caido el reloj sigue detenido; se corre cuando vuelve el ultimo.
    if pausa_abierta(db, sesion.id) is not None:
        return
    inicio_corte = _inicio_del_corte(db, pausa)
    detenido = momento - inicio_corte
    pendientes = db.execute(
        select(Bloque).where(Bloque.sesion_id == sesion.id, Bloque.estado == EstadoBloque.EN_CURSO)
    ).scalars()
    for bloque in pendientes:
        if bloque.hora_inicio >= inicio_corte:
            bloque.hora_inicio = bloque.hora_inicio + detenido
        bloque.hora_termino = bloque.hora_termino + detenido
    db.flush()


def _cerrar_por_caida(db: Session, sesion: Sesion, solicitud: Solicitud, caido_id: uuid.UUID, motivo: str) -> None:
    terminar(db, sesion, motivo)
    # Si el que se cayo es el tutor, el aprendiz no paga lo que estaba retenido.
    if caido_id == solicitud.tutor_id:
        for retencion in _retenciones_activas(db, sesion.id):
            tokens.reembolsar(db, retencion.id, "el tutor perdio la conexion")


# ---------------------------------------------------------------------------
# Cierre
# ---------------------------------------------------------------------------


def _retenciones_activas(db: Session, sesion_id: uuid.UUID) -> list[Retencion]:
    return list(
        db.execute(
            select(Retencion).where(Retencion.sesion_id == sesion_id, Retencion.estado == EstadoRetencion.ACTIVA)
        ).scalars()
    )


def terminar(db: Session, sesion: Sesion, motivo: str) -> None:
    momento = tokens.ahora()
    sesion.estado = EstadoSesion.TERMINADA
    sesion.fecha_cierre = momento
    sesion.motivo_cierre = motivo
    sesion.extension_propuesta_por = None
    sesion.fecha_propuesta_extension = None
    for pausa in db.execute(
        select(PausaSesion).where(PausaSesion.sesion_id == sesion.id, PausaSesion.estado == EstadoPausa.ABIERTA)
    ).scalars():
        pausa.estado = EstadoPausa.VENCIDA
        pausa.fin = momento
    abiertos = db.execute(
        select(Bloque).where(Bloque.sesion_id == sesion.id, Bloque.estado == EstadoBloque.EN_CURSO)
    ).scalars().all()
    for bloque in abiertos:
        if bloque.hora_inicio > momento:
            # Una extension que no alcanzo a empezar se devuelve.
            bloque.estado = EstadoBloque.ANULADO
            sesion.bloques_cobrados -= 1
            if bloque.retencion_id is not None:
                tokens.reembolsar(db, bloque.retencion_id, "la sesion termino antes de la extension")
        else:
            # El bloque empezado se cobra completo; solo se anota la hora real de termino.
            bloque.estado = EstadoBloque.COMPLETADO
            bloque.hora_termino = min(bloque.hora_termino, momento)
    db.flush()


def _cerrar_sala(sala: SalaLiveKit, sesion: Sesion) -> None:
    # Si LiveKit no responde, la sesion igual queda cerrada en Cachai.
    try:
        sala.cerrar(sesion.nombre_sala)
    except Exception:
        registro.warning("No se pudo cerrar la sala %s en LiveKit", sesion.nombre_sala)


def _cancelar(db: Session, sala: SalaLiveKit, sesion: Sesion, motivo: str) -> None:
    # Nadie alcanzo a usar la sala: todo lo retenido vuelve al aprendiz.
    sesion.estado = EstadoSesion.CANCELADA
    sesion.fecha_cierre = tokens.ahora()
    sesion.motivo_cierre = motivo
    for retencion in _retenciones_activas(db, sesion.id):
        tokens.reembolsar(db, retencion.id, motivo)
    _cerrar_sala(sala, sesion)
    db.flush()


# ---------------------------------------------------------------------------
# Acciones de los participantes durante la llamada
# ---------------------------------------------------------------------------


def _bloqueada(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> tuple[Sesion, Solicitud]:
    sesion, solicitud = _sesion_y_solicitud(db, usuario_id, sesion_id)
    db.refresh(sesion, with_for_update=True)
    return sesion, solicitud


def _en_curso(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> tuple[Sesion, Solicitud]:
    sesion, solicitud = _bloqueada(db, usuario_id, sesion_id)
    if sesion.estado != EstadoSesion.EN_CURSO:
        raise SesionNoEnCurso()
    return sesion, solicitud


def proponer_extension(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> Sesion:
    sesion, _ = _en_curso(db, usuario_id, sesion_id)
    if sesion.extension_propuesta_por is not None:
        raise ExtensionYaPropuesta()
    sesion.extension_propuesta_por = usuario_id
    sesion.fecha_propuesta_extension = tokens.ahora()
    db.flush()
    return sesion


def rechazar_extension(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> Sesion:
    # Sirve para rechazarla y tambien para retirarla.
    sesion, _ = _en_curso(db, usuario_id, sesion_id)
    if sesion.extension_propuesta_por is None:
        raise SinExtensionPendiente()
    sesion.extension_propuesta_por = None
    sesion.fecha_propuesta_extension = None
    db.flush()
    return sesion


def aceptar_extension(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> Sesion:
    sesion, solicitud = _en_curso(db, usuario_id, sesion_id)
    if sesion.extension_propuesta_por is None:
        raise SinExtensionPendiente()
    if sesion.extension_propuesta_por == usuario_id:
        raise ExtensionPropia()
    sesion.extension_propuesta_por = None
    sesion.fecha_propuesta_extension = None

    # Sin saldo la propuesta se descarta y la llamada termina con el bloque que ya corre.
    disponible = tokens.calcular_saldo(db, solicitud.aprendiz_id)
    if disponible < solicitud.precio_bloque:
        db.flush()
        raise tokens.SaldoInsuficiente(disponible, solicitud.precio_bloque)

    retencion = tokens.retener(db, solicitud.aprendiz_id, solicitud.precio_bloque)
    retencion.sesion_id = sesion.id
    ultimo = bloque_actual(db, sesion.id)
    minutos = parametros.obtener_entero(db, PARAM_DURACION_BLOQUE)
    db.add(
        Bloque(
            sesion_id=sesion.id,
            numero_orden=ultimo.numero_orden + 1,
            # El bloque nuevo empieza justo cuando termina el ultimo pagado.
            hora_inicio=ultimo.hora_termino,
            hora_termino=ultimo.hora_termino + timedelta(minutes=minutos),
            tokens_cobrados=solicitud.precio_bloque,
            retencion_id=retencion.id,
            estado=EstadoBloque.EN_CURSO,
        )
    )
    sesion.bloques_cobrados += 1
    db.flush()
    return sesion


def terminar_por_participante(db: Session, sala: SalaLiveKit, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> Sesion:
    sesion, solicitud = _bloqueada(db, usuario_id, sesion_id)
    quien = "el tutor" if usuario_id == solicitud.tutor_id else "el aprendiz"
    if sesion.estado == EstadoSesion.ESPERANDO:
        # Todavia no se cobraba nada: se cancela y el aprendiz recupera sus tokens.
        _cancelar(db, sala, sesion, f"{quien} cancelo antes de empezar")
        return sesion
    if sesion.estado != EstadoSesion.EN_CURSO:
        raise SesionNoEnCurso()
    terminar(db, sesion, f"{quien} termino la sesion")
    _cerrar_sala(sala, sesion)
    return sesion


# ---------------------------------------------------------------------------
# Procesos programados
# ---------------------------------------------------------------------------


def vencer_salas(db: Session, sala: SalaLiveKit) -> int:
    # Cancela las sesiones donde no se conectaron los dos a tiempo y devuelve los tokens.
    vencidas = db.execute(
        select(Sesion)
        .where(Sesion.estado == EstadoSesion.ESPERANDO, Sesion.fecha_limite_conexion <= tokens.ahora())
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for sesion in vencidas:
        _cancelar(db, sala, sesion, "no se conectaron los dos a tiempo")
    return len(vencidas)


def cerrar_bloques_terminados(db: Session, sala: SalaLiveKit) -> int:
    # Termina las sesiones sin tiempo pagado por delante. Con alguien caido el reloj esta detenido.
    momento = tokens.ahora()
    queda_tiempo = (
        select(Bloque.id)
        .where(Bloque.sesion_id == Sesion.id, Bloque.estado == EstadoBloque.EN_CURSO, Bloque.hora_termino > momento)
        .exists()
    )
    hay_pausa = (
        select(PausaSesion.id)
        .where(PausaSesion.sesion_id == Sesion.id, PausaSesion.estado == EstadoPausa.ABIERTA)
        .exists()
    )
    sesiones = db.execute(
        select(Sesion)
        .where(Sesion.estado == EstadoSesion.EN_CURSO, ~queda_tiempo, ~hay_pausa)
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for sesion in sesiones:
        terminar(db, sesion, "termino el tiempo pagado")
        _cerrar_sala(sala, sesion)
    return len(sesiones)


def vencer_pausas(db: Session, sala: SalaLiveKit) -> int:
    # Quien no volvio dentro del plazo hace terminar la sesion.
    vencidas = db.execute(
        select(PausaSesion)
        .where(PausaSesion.estado == EstadoPausa.ABIERTA, PausaSesion.limite_reconexion <= tokens.ahora())
        .with_for_update(skip_locked=True)
    ).scalars().all()

    cerradas = 0
    for pausa in vencidas:
        sesion = db.get(Sesion, pausa.sesion_id, with_for_update=True)
        if sesion.estado != EstadoSesion.EN_CURSO:
            continue
        solicitud = db.get(Solicitud, sesion.solicitud_id)
        _cerrar_por_caida(db, sesion, solicitud, pausa.usuario_id, "no volvio a conectarse a tiempo")
        _cerrar_sala(sala, sesion)
        cerradas += 1
    return cerradas


def liberar_pagos(db: Session) -> int:
    # Paga al tutor las sesiones cerradas hace mas del plazo de reporte.
    minutos = parametros.obtener_entero(db, PARAM_RETENCION_POSTERIOR)
    limite = tokens.ahora() - timedelta(minutes=minutos)
    pendientes = db.execute(
        select(Retencion.id, Solicitud.tutor_id)
        .join(Sesion, Sesion.id == Retencion.sesion_id)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .where(
            Sesion.estado == EstadoSesion.TERMINADA,
            Sesion.fecha_cierre <= limite,
            Retencion.estado == EstadoRetencion.ACTIVA,
        )
    ).all()

    for retencion_id, tutor_id in pendientes:
        tokens.liberar(db, retencion_id, tutor_id, motivo="sesion completada")
    return len(pendientes)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def _consulta():
    aprendiz = aliased(Usuario)
    tutor = aliased(Usuario)
    return (
        select(Sesion, Solicitud, Tema.nombre, aprendiz, tutor)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .join(HabilidadOfrecida, HabilidadOfrecida.id == Solicitud.habilidad_id)
        .join(Tema, Tema.id == HabilidadOfrecida.tema_id)
        .join(aprendiz, aprendiz.id == Solicitud.aprendiz_id)
        .join(tutor, tutor.id == Solicitud.tutor_id)
    )


def listar(db: Session, usuario_id: uuid.UUID, limite: int = 20) -> list[tuple]:
    sentencia = (
        _consulta()
        .where(or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id))
        .order_by(Sesion.fecha_apertura_sala.desc())
        .limit(limite)
    )
    return [tuple(fila) for fila in db.execute(sentencia).all()]


def detalle(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> tuple:
    fila = db.execute(
        _consulta().where(
            Sesion.id == sesion_id,
            or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id),
        )
    ).first()
    if fila is None:
        raise SesionNoEncontrada()
    return tuple(fila)


def bloque_actual(db: Session, sesion_id: uuid.UUID) -> Bloque | None:
    # El ultimo bloque pagado que sigue vigente (el de mayor numero sin anular).
    return db.execute(
        select(Bloque)
        .where(Bloque.sesion_id == sesion_id, Bloque.estado != EstadoBloque.ANULADO)
        .order_by(Bloque.numero_orden.desc())
        .limit(1)
    ).scalar_one_or_none()