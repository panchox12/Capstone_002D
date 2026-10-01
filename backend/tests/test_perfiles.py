"""Pruebas del perfil publico y codigos QR."""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seguridad import crear_token
from app.modelos.habilidad import EstadoHabilidad
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import habilidades as servicio_habilidades
from app.servicios import perfiles as servicio
from app.servicios import temas
from app.modelos.parametro import ParametroSistema


@pytest.fixture()
def usuario(db_prueba: Session) -> Usuario:
    u = Usuario(
        correo=f"{uuid.uuid4()}@prueba.cl",
        contrasena_hash="no-aplica",
        nombre_visible="Ana Lopez",
        estado_cuenta=EstadoCuenta.ACTIVA,
        consentimiento_grabacion=True,
    )
    db_prueba.add(u)
    db_prueba.flush()
    return u


def _cabecera(usuario: Usuario) -> dict:
    return {"Authorization": f"Bearer {crear_token(sujeto=str(usuario.id))}"}


# --- Servicio -------------------------------------------------------------------


def test_el_enlace_solo_admite_formato_valido(db_prueba: Session, usuario: Usuario) -> None:
    for invalido in ("ab", "con mayusculas", "con/barra", "a" * 31, "con@arroba"):
        with pytest.raises(servicio.EnlaceInvalido):
            servicio.actualizar_propio(db_prueba, usuario.id, enlace_personalizado=invalido)


def test_no_se_puede_tomar_un_enlace_en_uso(db_prueba: Session, usuario: Usuario) -> None:
    servicio.actualizar_propio(db_prueba, usuario.id, enlace_personalizado="ana-profe")

    otro = Usuario(
        correo=f"{uuid.uuid4()}@prueba.cl",
        contrasena_hash="no-aplica",
        nombre_visible="Otro",
        estado_cuenta=EstadoCuenta.ACTIVA,
        consentimiento_grabacion=True,
    )
    db_prueba.add(otro)
    db_prueba.flush()

    with pytest.raises(servicio.EnlaceEnUso):
        servicio.actualizar_propio(db_prueba, otro.id, enlace_personalizado="ana-profe")


def test_se_puede_buscar_por_uuid_o_por_enlace(db_prueba: Session, usuario: Usuario) -> None:
    servicio.actualizar_propio(db_prueba, usuario.id, enlace_personalizado="ana-profe")

    u1, p1 = servicio.obtener_publico(db_prueba, str(usuario.id))
    u2, p2 = servicio.obtener_publico(db_prueba, "ana-profe")

    assert u1.id == u2.id == usuario.id
    assert p1.enlace_personalizado == p2.enlace_personalizado == "ana-profe"


def test_un_usuario_suspendido_no_tiene_perfil_publico(db_prueba: Session, usuario: Usuario) -> None:
    servicio.actualizar_propio(db_prueba, usuario.id, enlace_personalizado="ana-profe")
    usuario.estado_cuenta = EstadoCuenta.SUSPENDIDA
    db_prueba.flush()

    with pytest.raises(servicio.PerfilNoEncontrado):
        servicio.obtener_publico(db_prueba, "ana-profe")


def test_el_qr_devuelve_bytes_png() -> None:
    png = servicio.generar_qr_png("https://ejemplo.com/u/ana-profe")

    assert isinstance(png, bytes)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


# --- Endpoints ------------------------------------------------------------------


def test_actualizar_y_ver_perfil(cliente_db: TestClient, db_prueba: Session, usuario: Usuario) -> None:
    # Asegurar parametro del sistema para validar precios de habilidades
    db_prueba.add(ParametroSistema(nombre=servicio_habilidades.PARAM_PRECIO_MAXIMO, valor="0"))
    db_prueba.flush()

    raiz = temas.crear(db_prueba, "Ciencias")
    grupo = temas.crear(db_prueba, "Fisica", raiz.id)
    hoja = temas.crear(db_prueba, "Optica", grupo.id)
    servicio_habilidades.publicar(db_prueba, usuario.id, hoja.id, 2)

    respuesta = cliente_db.patch(
        "/perfiles/mio",
        json={"biografia": "Clases de optica para ingenieria", "enlace_personalizado": "ana-optica"},
        headers=_cabecera(usuario),
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["enlace_personalizado"] == "ana-optica"
    assert len(cuerpo["habilidades"]) == 1
    assert cuerpo["habilidades"][0]["tema_nombre"] == "Optica"

    publico = cliente_db.get("/perfiles/ana-optica")
    assert publico.status_code == 200
    assert publico.json()["biografia"] == "Clases de optica para ingenieria"

def test_el_endpoint_qr_devuelve_imagen_png(cliente_db: TestClient, db_prueba: Session, usuario: Usuario) -> None:
    servicio.actualizar_propio(db_prueba, usuario.id, enlace_personalizado="ana-optica")

    respuesta = cliente_db.get("/perfiles/ana-optica/qr")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.content.startswith(b"\x89PNG\r\n\x1a\n")