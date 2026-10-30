"""Punto de entrada de la API de Cachai."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import configuracion
from app.procesos import planificador
from app.routers import salud, auth, verificacion, temas, habilidades, perfiles, tokens, tienda, solicitudes, presencia, buscador, sesiones


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lo que corre al levantar la API (antes del yield) y al apagarla (despues)."""
    if configuracion.planificador_activo:
        planificador.iniciar()
    yield
    if configuracion.planificador_activo:
        planificador.detener()


app = FastAPI(
    title=configuracion.app_nombre,
    description="Plataforma de microconsultas en vivo con moneda interna.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[configuracion.url_frontend],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(salud.router)
app.include_router(auth.router)
app.include_router(verificacion.router)
app.include_router(temas.router)
app.include_router(habilidades.router)
app.include_router(perfiles.router)
app.include_router(tokens.router)
app.include_router(tienda.router)
app.include_router(solicitudes.router)
app.include_router(presencia.router)
app.include_router(buscador.router)
app.include_router(sesiones.router)


@app.get("/", tags=["Raiz"])
def raiz() -> dict:
    return {
        "mensaje": f"API de {configuracion.app_nombre}",
        "version": "0.1.0",
        "documentacion": "/docs",
    }