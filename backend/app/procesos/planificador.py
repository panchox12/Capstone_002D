"""Procesos programados del backend.
"""

import logging
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.db.sesion import SesionLocal
from app.servicios import entradas, solicitudes

registro = logging.getLogger("uvicorn.error")

ZONA_HORARIA = "America/Santiago"
SEGUNDOS_ENTRE_REVISIONES = 10

planificador = BackgroundScheduler(timezone=ZONA_HORARIA)


def _ejecutar(nombre: str, tarea: Callable[[Session], int]) -> None:
    # Cada tarea abre su propia sesion. si falla, se deshace y se anota en la terminal.
    db = SesionLocal()
    try:
        cantidad = tarea(db)
        db.commit()
        if cantidad:
            registro.info("Proceso '%s': %s", nombre, cantidad)
    except Exception:
        db.rollback()
        registro.exception("Fallo el proceso '%s'", nombre)
    finally:
        db.close()


def vencer_solicitudes() -> None:
    _ejecutar("solicitudes vencidas", solicitudes.vencer_atrasadas)


def entrega_semanal() -> None:
    _ejecutar("entrega semanal", entradas.entregar_semanal_a_todos)


def vencer_lotes() -> None:
    _ejecutar("lotes vencidos", entradas.vencer_lotes)


def registrar_tareas() -> None:
    # Cada diez segundos, sin encimarse si una revision tarda.
    planificador.add_job(
        vencer_solicitudes,
        "interval",
        seconds=SEGUNDOS_ENTRE_REVISIONES,
        id="vencer_solicitudes",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    # Los lunes a las 00:05.
    planificador.add_job(
        entrega_semanal,
        CronTrigger(day_of_week="mon", hour=0, minute=5, timezone=ZONA_HORARIA),
        id="entrega_semanal",
        replace_existing=True,
    )
    # Todos los dias a las 00:15.
    planificador.add_job(
        vencer_lotes,
        CronTrigger(hour=0, minute=15, timezone=ZONA_HORARIA),
        id="vencer_lotes",
        replace_existing=True,
    )


def iniciar() -> None:
    registrar_tareas()
    planificador.start()


def detener() -> None:
    planificador.shutdown(wait=False)