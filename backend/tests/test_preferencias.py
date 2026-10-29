"""Pruebas de las preferencias de presencia: aparecer conectado y recibir solicitudes diferidas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.solicitud import ModalidadSolicitud
from app.servicios import habilidades, perfiles, presencia, solicitudes, temas, tokens
from tests.utilidades import cabecera, crear_usuario


def test_sin_perfil_guardado_las_dos_preferencias_parten_activas(
    db_prueba: Session, cliente_db: TestClient
) -> None:
    usuario = crear_usuario(db_prueba)

    respuesta = cliente_db.get("/perfiles/mio/preferencias", headers=cabecera(usuario))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mostrar_en_linea": True, "acepta_diferidas": True}


def test_se_puede_cambiar_una_sola_preferencia(db_prueba: Session, cliente_db: TestClient) -> None:
    usuario = crear_usuario(db_prueba)

    respuesta = cliente_db.patch(
        "/perfiles/mio/preferencias", headers=cabecera(usuario), json={"acepta_diferidas": False}
    )

    assert respuesta.json() == {"mostrar_en_linea": True, "acepta_diferidas": False}
    assert perfiles.preferencias(db_prueba, usuario.id).acepta_diferidas is False


def test_las_preferencias_exigen_sesion(cliente_db: TestClient) -> None:
    assert cliente_db.get("/perfiles/mio/preferencias").status_code == 401


def test_ocultarse_lo_desconecta_de_inmediato(db_prueba: Session, cliente_db: TestClient, redis_falso) -> None:
    usuario = crear_usuario(db_prueba)
    presencia.marcar_en_linea(redis_falso, usuario.id)

    cliente_db.patch("/perfiles/mio/preferencias", headers=cabecera(usuario), json={"mostrar_en_linea": False})

    assert not presencia.esta_en_linea(redis_falso, usuario.id)


def test_oculto_el_latido_no_lo_muestra_en_linea(db_prueba: Session, cliente_db: TestClient, redis_falso) -> None:
    usuario = crear_usuario(db_prueba)
    perfiles.actualizar_preferencias(db_prueba, usuario.id, mostrar_en_linea=False)

    respuesta = cliente_db.post("/presencia/latido", headers=cabecera(usuario))

    assert respuesta.status_code == 204
    assert not presencia.esta_en_linea(redis_falso, usuario.id)


def test_visible_el_latido_lo_sigue_mostrando_en_linea(
    db_prueba: Session, cliente_db: TestClient, redis_falso
) -> None:
    usuario = crear_usuario(db_prueba)

    cliente_db.post("/presencia/latido", headers=cabecera(usuario))

    assert presencia.esta_en_linea(redis_falso, usuario.id)


@pytest.mark.usefixtures("parametros_iniciales")
def test_a_un_tutor_oculto_le_llegan_solicitudes_diferidas(
    db_prueba: Session, cliente_db: TestClient, redis_falso
) -> None:
    tutor = crear_usuario(db_prueba, nombre="Rodrigo Salas", verificado=True)
    aprendiz = crear_usuario(db_prueba, nombre="Valentina Rojas", verificado=True)
    tokens.otorgar(db_prueba, aprendiz.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    raiz = temas.crear(db_prueba, "Ciencias exactas")
    grupo = temas.crear(db_prueba, "Matematicas", raiz.id)
    habilidad = habilidades.publicar(db_prueba, tutor.id, temas.crear(db_prueba, "Algebra", grupo.id).id, 3)
    perfiles.actualizar_preferencias(db_prueba, tutor.id, mostrar_en_linea=False)
    cliente_db.post("/presencia/latido", headers=cabecera(tutor))

    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Ayuda con factorizar")

    assert solicitud.modalidad == ModalidadSolicitud.DIFERIDA