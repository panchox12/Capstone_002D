"""Endpoints de diagnostico.

Sirven para que tu, tu monitoreo y AWS puedan preguntar
si el sistema esta vivo sin tocar logica de negocio.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.db.sesion import obtener_db

router = APIRouter(prefix="/salud", tags=["Salud"])


@router.get("", summary="Estado general del servicio")
def estado_general() -> dict:
    return {
        "estado": "ok",
        "servicio": configuracion.app_nombre,
        "entorno": configuracion.app_entorno,
    }


@router.get("/db", summary="Estado de la conexion a la base de datos")
def estado_base_datos(db: Session = Depends(obtener_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"estado": "ok", "base_datos": "conectada"}