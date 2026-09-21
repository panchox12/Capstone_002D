"""Conexion y sesiones de base de datos."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import configuracion

motor = create_engine(
    configuracion.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=configuracion.app_debug,
)

SesionLocal = sessionmaker(
    bind=motor,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def obtener_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesion y garantiza su cierre."""
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()