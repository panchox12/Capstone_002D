"""Reportes de sesiones y su resolucion por soporte.

Reglas que este modulo garantiza:
- Solo reporta quien participo, en una sesion terminada y dentro del plazo (48 horas).
- Si el reporte llega mientras el pago del tutor sigue retenido, el pago se congela
  hasta que soporte lo resuelva.
- Un reporte fundado del aprendiz le devuelve lo que pago: lo retenido vuelve a sus lotes,
  y si el tutor ya habia cobrado, la plataforma lo compensa con un lote nuevo.
- Toda sancion queda con el folio del reporte, la justificacion y el revisor.
Ninguna funcion hace commit: quien la llama confirma todo junto, o nada.
"""

import uuid
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.modelos.habilidad import HabilidadOfrecida
from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.moderacion import EstadoReporte, MotivoReporte, Reporte, Sancion, TipoSancion
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.sesion import EstadoSesion, Sesion
from app.modelos.solicitud import Solicitud
from app.modelos.tema import Tema
from app.modelos.transaccion import TipoTransaccion
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import notificaciones, parametros, tokens

PARAM_PLAZO_REPORTE = "plazo_reporte_horas"


class SesionNoReportable(Exception):
    # No existe, no participaste o todavia no termina.
    pass


class PlazoDeReporteVencido(Exception):
    pass


class ReporteDuplicado(Exception):
    pass


class ReporteNoEncontrado(Exception):
    pass


class ReporteYaResuelto(Exception):
    pass


class SancionSinFundamento(Exception):
    # Solo se sanciona con un reporte fundado.
    pass


# ---------------------------------------------------------------------------
# Reportar
# ---------------------------------------------------------------------------


def crear(
    db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID, motivo: MotivoReporte, descripcion: str
) -> Reporte:
    fila = db.execute(
        select(Sesion, Solicitud)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .where(Sesion.id == sesion_id, or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id))
    ).first()
    if fila is None or fila[0].estado != EstadoSesion.TERMINADA:
        raise SesionNoReportable()
    sesion, solicitud = fila

    horas = parametros.obtener_entero(db, PARAM_PLAZO_REPORTE)
    if tokens.ahora() > sesion.fecha_cierre + timedelta(hours=horas):
        raise PlazoDeReporteVencido()

    ya_existe = db.execute(
        select(Reporte.id).where(Reporte.sesion_id == sesion.id, Reporte.reportante_id == usuario_id)
    ).first()
    if ya_existe is not None:
        raise ReporteDuplicado()

    # Si todavia hay tokens retenidos, el tutor no cobra hasta que soporte resuelva.
    retenido = db.execute(
        select(Retencion.id).where(Retencion.sesion_id == sesion.id, Retencion.estado == EstadoRetencion.ACTIVA)
    ).first()
    otro = solicitud.tutor_id if usuario_id == solicitud.aprendiz_id else solicitud.aprendiz_id
    reporte = Reporte(
        sesion_id=sesion.id,
        reportante_id=usuario_id,
        reportado_id=otro,
        motivo=motivo,
        descripcion=descripcion.strip(),
        estado=EstadoReporte.ABIERTO,
        congela_pago=retenido is not None,
    )
    db.add(reporte)
    db.flush()
    return reporte


def propios(db: Session, usuario_id: uuid.UUID) -> list[Reporte]:
    return list(
        db.execute(
            select(Reporte).where(Reporte.reportante_id == usuario_id).order_by(Reporte.creado_en.desc())
        ).scalars()
    )


# ---------------------------------------------------------------------------
# Soporte
# ---------------------------------------------------------------------------


def _consulta():
    reportante = aliased(Usuario)
    reportado = aliased(Usuario)
    return (
        select(Reporte, Sesion, Solicitud, Tema.nombre, reportante, reportado)
        .join(Sesion, Sesion.id == Reporte.sesion_id)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .join(HabilidadOfrecida, HabilidadOfrecida.id == Solicitud.habilidad_id)
        .join(Tema, Tema.id == HabilidadOfrecida.tema_id)
        .join(reportante, reportante.id == Reporte.reportante_id)
        .join(reportado, reportado.id == Reporte.reportado_id)
    )


def listar(db: Session, estado: EstadoReporte | None = None) -> list[tuple]:
    sentencia = _consulta().order_by(Reporte.folio.desc())
    if estado is not None:
        sentencia = sentencia.where(Reporte.estado == estado)
    return [tuple(fila) for fila in db.execute(sentencia).all()]


def detalle(db: Session, reporte_id: uuid.UUID) -> tuple:
    fila = db.execute(_consulta().where(Reporte.id == reporte_id)).first()
    if fila is None:
        raise ReporteNoEncontrado()
    return tuple(fila)


def resumen_de_pago(db: Session, sesion_id: uuid.UUID) -> dict[str, int]:
    # Cuantos tokens de la sesion siguen retenidos, se pagaron al tutor o volvieron al aprendiz.
    resumen = {"retenido": 0, "pagado": 0, "devuelto": 0}
    clave = {
        EstadoRetencion.ACTIVA: "retenido",
        EstadoRetencion.LIBERADA: "pagado",
        EstadoRetencion.REEMBOLSADA: "devuelto",
    }
    for retencion in db.execute(select(Retencion).where(Retencion.sesion_id == sesion_id)).scalars():
        resumen[clave[retencion.estado]] += retencion.cantidad
    return resumen


def sanciones_previas(db: Session, usuario_id: uuid.UUID) -> int:
    return len(db.execute(select(Sancion.id).where(Sancion.usuario_id == usuario_id)).all())


def _compensar_aprendiz(db: Session, sesion: Sesion, aprendiz_id: uuid.UUID) -> None:
    retenciones = db.execute(select(Retencion).where(Retencion.sesion_id == sesion.id)).scalars().all()
    compensar = 0
    for retencion in retenciones:
        if retencion.estado == EstadoRetencion.ACTIVA:
            tokens.reembolsar(db, retencion.id, "reporte fundado")
        elif retencion.estado == EstadoRetencion.LIBERADA:
            compensar += retencion.cantidad
    # El tutor ya cobro: no se le quita, paga la plataforma desde su cuenta de contingencia.
    if compensar:
        tokens.otorgar(
            db,
            usuario_id=aprendiz_id,
            cantidad=compensar,
            tipo_saldo=TipoSaldo.PAGADO,
            origen=OrigenLote.COMPENSACION,
            dias_vigencia=tokens.dias_de_vigencia(db, OrigenLote.COMPENSACION),
            tipo_transaccion=TipoTransaccion.COMPENSACION,
        )


def resolver(
    db: Session,
    revisor_id: uuid.UUID,
    reporte_id: uuid.UUID,
    fundado: bool,
    resolucion: str,
    tipo_sancion: TipoSancion | None = None,
    dias_suspension: int | None = None,
) -> Reporte:
    reporte = db.get(Reporte, reporte_id, with_for_update=True)
    if reporte is None:
        raise ReporteNoEncontrado()
    if reporte.estado != EstadoReporte.ABIERTO:
        raise ReporteYaResuelto()
    if tipo_sancion is not None and not fundado:
        raise SancionSinFundamento()

    momento = tokens.ahora()
    reporte.estado = EstadoReporte.FUNDADO if fundado else EstadoReporte.DESESTIMADO
    reporte.revisor_id = revisor_id
    reporte.resolucion = resolucion.strip()
    reporte.fecha_resolucion = momento

    sesion = db.get(Sesion, reporte.sesion_id)
    solicitud = db.get(Solicitud, sesion.solicitud_id)
    if fundado and reporte.reportante_id == solicitud.aprendiz_id:
        _compensar_aprendiz(db, sesion, solicitud.aprendiz_id)

    resultado = "fundado" if fundado else "desestimado"
    notificaciones.avisar(
        db,
        reporte.reportante_id,
        "reporte_resuelto",
        f"Tu reporte {reporte.folio} fue resuelto",
        f"Soporte lo considero {resultado}: {reporte.resolucion}",
        "/sesiones",
    )

    if tipo_sancion is not None:
        fin = momento + timedelta(days=dias_suspension) if tipo_sancion == TipoSancion.TEMPORAL else None
        db.add(
            Sancion(
                usuario_id=reporte.reportado_id,
                reporte_id=reporte.id,
                revisor_id=revisor_id,
                tipo=tipo_sancion,
                justificacion=reporte.resolucion,
                fecha_inicio=momento,
                fecha_fin=fin,
            )
        )
        sancionado = db.get(Usuario, reporte.reportado_id, with_for_update=True)
        sancionado.estado_cuenta = EstadoCuenta.SUSPENDIDA
        sancionado.suspendido_hasta = fin
        duracion = f"hasta el {fin:%d-%m-%Y}" if fin else "de forma definitiva"
        # Va por correo: con la cuenta suspendida no puede entrar a ver la campana.
        notificaciones.avisar(
            db,
            sancionado.id,
            "sancion",
            "Tu cuenta fue suspendida",
            f"Por el reporte {reporte.folio}, tu cuenta queda suspendida {duracion}. Motivo: {reporte.resolucion}",
            por_correo=True,
        )
    db.flush()
    return reporte


# ---------------------------------------------------------------------------
# Proceso programado
# ---------------------------------------------------------------------------


def reactivar_suspensiones(db: Session) -> int:
    # Las suspensiones temporales vencidas devuelven la cuenta a activa.
    vencidas = db.execute(
        select(Usuario)
        .where(
            Usuario.estado_cuenta == EstadoCuenta.SUSPENDIDA,
            Usuario.suspendido_hasta.is_not(None),
            Usuario.suspendido_hasta <= tokens.ahora(),
        )
        .with_for_update(skip_locked=True)
    ).scalars().all()
    for usuario in vencidas:
        usuario.estado_cuenta = EstadoCuenta.ACTIVA
        usuario.suspendido_hasta = None
    db.flush()
    return len(vencidas)