"""Sesiones: ver las propias, entrar a la sala, extenderla o terminarla, y recibir los avisos de LiveKit."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.sesion import PermisoSala, SesionLeer
from app.esquemas.solicitud import Participante
from app.modelos.sesion import EstadoSesion
from app.modelos.usuario import Usuario
from app.servicios import parametros, tokens
from app.servicios import sesiones as servicio
from app.servicios.sala import EventoInvalido, SalaLiveKit, SalaNoConfigurada, obtener_sala

router = APIRouter(prefix="/sesiones", tags=["Sesiones"])

NO_ENCONTRADA = HTTPException(status.HTTP_404_NOT_FOUND, "Sesion no encontrada")
NO_EN_CURSO = HTTPException(status.HTTP_409_CONFLICT, "La sesion no esta en curso")


def _segundos_hasta(momento) -> int:
    return max(0, int((momento - tokens.ahora()).total_seconds()))


def _leer(db: Session, fila: tuple) -> SesionLeer:
    sesion, solicitud, tema_nombre, aprendiz, tutor = fila
    para_conectarse = 0
    if sesion.estado == EstadoSesion.ESPERANDO:
        para_conectarse = _segundos_hasta(sesion.fecha_limite_conexion)
    restantes_bloque = 0
    pausa = None
    if sesion.estado == EstadoSesion.EN_CURSO:
        bloque = servicio.bloque_actual(db, sesion.id)
        pausa = servicio.pausa_abierta(db, sesion.id)
        if pausa is not None:
            # Con alguien caido el reloj queda detenido donde estaba.
            restantes_bloque = max(0, int((bloque.hora_termino - pausa.inicio).total_seconds()))
        else:
            restantes_bloque = _segundos_hasta(bloque.hora_termino)
    return SesionLeer(
        id=sesion.id,
        solicitud_id=solicitud.id,
        estado=sesion.estado,
        tema_nombre=tema_nombre,
        precio_bloque=solicitud.precio_bloque,
        aprendiz=Participante(id=aprendiz.id, nombre_visible=aprendiz.nombre_visible),
        tutor=Participante(id=tutor.id, nombre_visible=tutor.nombre_visible),
        fecha_apertura_sala=sesion.fecha_apertura_sala,
        fecha_limite_conexion=sesion.fecha_limite_conexion,
        fecha_conexion_ambos=sesion.fecha_conexion_ambos,
        fecha_cierre=sesion.fecha_cierre,
        bloques_cobrados=sesion.bloques_cobrados,
        motivo_cierre=sesion.motivo_cierre,
        segundos_para_conectarse=para_conectarse,
        segundos_restantes_bloque=restantes_bloque,
        extension_propuesta_por=sesion.extension_propuesta_por,
        pausa_activa=pausa is not None,
        usuario_caido_id=pausa.usuario_id if pausa else None,
        segundos_para_reconectar=_segundos_hasta(pausa.limite_reconexion) if pausa else 0,
        pausas_usadas=servicio.contar_pausas(db, sesion.id),
        pausas_maximas=parametros.obtener_entero(db, servicio.PARAM_PAUSAS_MAXIMAS),
    )


@router.get("", response_model=list[SesionLeer], summary="Mis sesiones, la mas nueva primero")
def mis_sesiones(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> list[SesionLeer]:
    return [_leer(db, fila) for fila in servicio.listar(db, usuario.id)]


@router.get("/{sesion_id}", response_model=SesionLeer, summary="Ver una sesion")
def ver_sesion(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> SesionLeer:
    try:
        return _leer(db, servicio.detalle(db, usuario.id, sesion_id))
    except servicio.SesionNoEncontrada:
        raise NO_ENCONTRADA from None


@router.post("/{sesion_id}/entrar", response_model=PermisoSala, summary="Permiso para entrar a la sala")
def entrar(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
    sala: SalaLiveKit = Depends(obtener_sala),
) -> PermisoSala:
    try:
        sesion, permiso = servicio.entrar(db, sala, usuario, sesion_id)
    except servicio.SesionNoEncontrada:
        raise NO_ENCONTRADA from None
    except servicio.SalaCerrada:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta sesion ya termino") from None
    except SalaNoConfigurada:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "La videollamada no esta disponible") from None
    return PermisoSala(url=configuracion.livekit_url, token=permiso, nombre_sala=sesion.nombre_sala)


def _actuar(db: Session, usuario: Usuario, sesion_id: uuid.UUID, accion) -> SesionLeer:
    # Ejecuta una accion sobre la sesion y traduce los errores a respuestas HTTP.
    try:
        accion()
    except servicio.SesionNoEncontrada:
        raise NO_ENCONTRADA from None
    except servicio.SesionNoEnCurso:
        raise NO_EN_CURSO from None
    except servicio.ExtensionYaPropuesta:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya hay una extension esperando respuesta") from None
    except servicio.SinExtensionPendiente:
        raise HTTPException(status.HTTP_409_CONFLICT, "No hay ninguna extension propuesta") from None
    except servicio.ExtensionPropia:
        raise HTTPException(status.HTTP_409_CONFLICT, "La extension la tiene que aceptar la otra persona") from None
    except tokens.SaldoInsuficiente as error:
        # La propuesta descartada se guarda igual.
        db.commit()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Al aprendiz no le alcanza para otro bloque: tiene {error.disponible} tokens y cuesta {error.requerido}",
        ) from None
    db.commit()
    return _leer(db, servicio.detalle(db, usuario.id, sesion_id))


@router.post("/{sesion_id}/extension", response_model=SesionLeer, summary="Proponer un bloque mas")
def proponer_extension(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> SesionLeer:
    return _actuar(db, usuario, sesion_id, lambda: servicio.proponer_extension(db, usuario.id, sesion_id))


@router.post("/{sesion_id}/extension/aceptar", response_model=SesionLeer, summary="Aceptar la extension propuesta")
def aceptar_extension(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> SesionLeer:
    return _actuar(db, usuario, sesion_id, lambda: servicio.aceptar_extension(db, usuario.id, sesion_id))


@router.post("/{sesion_id}/extension/rechazar", response_model=SesionLeer, summary="Rechazar o retirar la extension")
def rechazar_extension(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> SesionLeer:
    return _actuar(db, usuario, sesion_id, lambda: servicio.rechazar_extension(db, usuario.id, sesion_id))


@router.post("/{sesion_id}/terminar", response_model=SesionLeer, summary="Terminar la sesion antes de tiempo")
def terminar(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
    sala: SalaLiveKit = Depends(obtener_sala),
) -> SesionLeer:
    return _actuar(db, usuario, sesion_id, lambda: servicio.terminar_por_participante(db, sala, usuario.id, sesion_id))


def _procesar(db: Session, evento) -> None:
    servicio.registrar_evento(db, evento)
    db.commit()


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT, summary="Avisos de LiveKit")
async def webhook(
    request: Request,
    db: Session = Depends(obtener_db),
    sala: SalaLiveKit = Depends(obtener_sala),
) -> Response:
    # La firma se comprueba con el cuerpo exacto que llego, por eso se lee crudo.
    cuerpo = (await request.body()).decode("utf-8")
    try:
        evento = sala.leer_evento(cuerpo, request.headers.get("Authorization", ""))
    except (EventoInvalido, SalaNoConfigurada):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Aviso no reconocido") from None

    await run_in_threadpool(_procesar, db, evento)
    return Response(status_code=status.HTTP_204_NO_CONTENT)