"""Panel de soporte: revisar reportes y resolverlos. Solo para soporte y administradores."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.dependencias import usuario_con_rol
from app.esquemas.reporte import PagoSesion, ReporteDetalle, ReporteResumen, Resolucion
from app.esquemas.solicitud import Participante
from app.modelos.moderacion import EstadoReporte
from app.modelos.usuario import RolUsuario, Usuario
from app.servicios import reportes as servicio

router = APIRouter(prefix="/soporte", tags=["Soporte"])

personal_de_soporte = usuario_con_rol(RolUsuario.SOPORTE, RolUsuario.ADMINISTRADOR)

NO_ENCONTRADO = HTTPException(status.HTTP_404_NOT_FOUND, "Reporte no encontrado")


def _resumen(fila: tuple) -> dict:
    reporte, _sesion, _solicitud, tema_nombre, reportante, reportado = fila
    return {
        "id": reporte.id,
        "folio": reporte.folio,
        "motivo": reporte.motivo,
        "estado": reporte.estado,
        "congela_pago": reporte.congela_pago,
        "tema_nombre": tema_nombre,
        "reportante": Participante(id=reportante.id, nombre_visible=reportante.nombre_visible),
        "reportado": Participante(id=reportado.id, nombre_visible=reportado.nombre_visible),
        "creado_en": reporte.creado_en,
    }


def _detalle(db: Session, fila: tuple) -> ReporteDetalle:
    reporte, sesion, solicitud, _tema, _reportante, reportado = fila
    return ReporteDetalle(
        **_resumen(fila),
        descripcion=reporte.descripcion,
        resolucion=reporte.resolucion,
        fecha_resolucion=reporte.fecha_resolucion,
        sesion_id=sesion.id,
        estado_sesion=sesion.estado,
        precio_bloque=solicitud.precio_bloque,
        bloques_cobrados=sesion.bloques_cobrados,
        fecha_conexion_ambos=sesion.fecha_conexion_ambos,
        fecha_cierre=sesion.fecha_cierre,
        motivo_cierre=sesion.motivo_cierre,
        pago=PagoSesion(**servicio.resumen_de_pago(db, sesion.id)),
        sanciones_previas_reportado=servicio.sanciones_previas(db, reportado.id),
    )


@router.get("/reportes", response_model=list[ReporteResumen], summary="Bandeja de reportes")
def bandeja(
    estado: EstadoReporte | None = None,
    _personal: Usuario = Depends(personal_de_soporte),
    db: Session = Depends(obtener_db),
) -> list[ReporteResumen]:
    return [ReporteResumen(**_resumen(fila)) for fila in servicio.listar(db, estado)]


@router.get("/reportes/{reporte_id}", response_model=ReporteDetalle, summary="Ver un reporte")
def ver_reporte(
    reporte_id: uuid.UUID,
    _personal: Usuario = Depends(personal_de_soporte),
    db: Session = Depends(obtener_db),
) -> ReporteDetalle:
    try:
        return _detalle(db, servicio.detalle(db, reporte_id))
    except servicio.ReporteNoEncontrado:
        raise NO_ENCONTRADO from None


@router.post("/reportes/{reporte_id}/resolver", response_model=ReporteDetalle, summary="Resolver un reporte")
def resolver(
    reporte_id: uuid.UUID,
    datos: Resolucion,
    personal: Usuario = Depends(personal_de_soporte),
    db: Session = Depends(obtener_db),
) -> ReporteDetalle:
    try:
        servicio.resolver(
            db, personal.id, reporte_id, datos.fundado, datos.resolucion, datos.tipo_sancion, datos.dias_suspension
        )
    except servicio.ReporteNoEncontrado:
        raise NO_ENCONTRADO from None
    except servicio.ReporteYaResuelto:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este reporte ya fue resuelto") from None
    except servicio.SancionSinFundamento:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Solo se sanciona con un reporte fundado") from None
    db.commit()
    return _detalle(db, servicio.detalle(db, reporte_id))