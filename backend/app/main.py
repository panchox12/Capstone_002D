"""Punto de entrada de la API de Cachai."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import configuracion
from app.routers import salud, auth, verificacion

app = FastAPI(
    title=configuracion.app_nombre,
    description="Plataforma de microconsultas en vivo con moneda interna.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(salud.router)
app.include_router(auth.router)
app.include_router(verificacion.router)

@app.get("/", tags=["Raiz"])
def raiz() -> dict:
    return {
        "mensaje": f"API de {configuracion.app_nombre}",
        "version": "0.1.0",
        "documentacion": "/docs",
    }