"""Reportes de los usuarios: reportar una sesion y ver los propios."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.reporte import ReporteCrear, ReporteLeer
from app.modelos.usuario import Usuario
from app.servicios import reportes as servicio

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.post("", response_model=ReporteLeer, status_code=status.HTTP_201_CREATED, summary="Reportar una sesion")
def reportar(
    datos: ReporteCrear,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> ReporteLeer:
    try:
        reporte = servicio.crear(db, usuario.id, datos.sesion_id, datos.motivo, datos.descripcion)
    except servicio.SesionNoReportable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay una sesion terminada tuya con ese numero") from None
    except servicio.PlazoDeReporteVencido:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya paso el plazo para reportar esta sesion") from None
    except servicio.ReporteDuplicado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya reportaste esta sesion") from None
    except IntegrityError:
        # Dos envios en el mismo instante: la restriccion unica frena al segundo.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya reportaste esta sesion") from None
    db.commit()
    return reporte


@router.get("/mios", response_model=list[ReporteLeer], summary="Mis reportes y su estado")
def mis_reportes(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> list[ReporteLeer]:
    return servicio.propios(db, usuario.id)