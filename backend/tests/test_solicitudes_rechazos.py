"""Pruebas de cuando una solicitud no se puede enviar: bloqueos y tutores que no reciben diferidas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.moderacion import Bloqueo
from app.modelos.solicitud import ModalidadSolicitud
from app.servicios import habilidades, perfiles, presencia, solicitudes, temas, tokens
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


@pytest.fixture()
def tutor(db_prueba: Session):
    return crear_usuario(db_prueba, nombre="Rodrigo Salas", verificado=True)


@pytest.fixture()
def aprendiz(db_prueba: Session):
    usuario = crear_usuario(db_prueba, nombre="Valentina Rojas", verificado=True)
    tokens.otorgar(db_prueba, usuario.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    return usuario


@pytest.fixture()
def habilidad(db_prueba: Session, tutor):
    raiz = temas.crear(db_prueba, "Oficios")
    grupo = temas.crear(db_prueba, "Electricidad", raiz.id)
    tema = temas.crear(db_prueba, "Enchufes", grupo.id)
    return habilidades.publicar(db_prueba, tutor.id, tema.id, 2)


def test_tutor_desconectado_que_no_recibe_diferidas_no_recibe_nada(
    db_prueba: Session, redis_falso, tutor, aprendiz, habilidad
) -> None:
    perfiles.actualizar_preferencias(db_prueba, tutor.id, acepta_diferidas=False)

    with pytest.raises(solicitudes.TutorNoRecibeDiferidas):
        solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Un enchufe suelta chispas")


def test_si_esta_conectado_igual_recibe_en_vivo(db_prueba: Session, redis_falso, tutor, aprendiz, habilidad) -> None:
    perfiles.actualizar_preferencias(db_prueba, tutor.id, acepta_diferidas=False)
    presencia.marcar_en_linea(redis_falso, tutor.id)

    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Un enchufe suelta chispas")

    assert solicitud.modalidad == ModalidadSolicitud.EN_VIVO


def test_sin_perfil_guardado_si_recibe_diferidas(db_prueba: Session, redis_falso, aprendiz, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Un enchufe suelta chispas")

    assert solicitud.modalidad == ModalidadSolicitud.DIFERIDA


@pytest.mark.parametrize("quien_bloquea", ["aprendiz", "tutor"])
def test_un_bloqueo_en_cualquier_direccion_impide_la_solicitud(
    db_prueba: Session, redis_falso, tutor, aprendiz, habilidad, quien_bloquea
) -> None:
    presencia.marcar_en_linea(redis_falso, tutor.id)
    uno, otro = (aprendiz, tutor) if quien_bloquea == "aprendiz" else (tutor, aprendiz)
    db_prueba.add(Bloqueo(bloqueador_id=uno.id, bloqueado_id=otro.id))
    db_prueba.flush()

    with pytest.raises(solicitudes.UsuarioBloqueado):
        solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Un enchufe suelta chispas")
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 10


def test_la_api_explica_cada_rechazo(cliente_db: TestClient, db_prueba: Session, tutor, aprendiz, habilidad) -> None:
    perfiles.actualizar_preferencias(db_prueba, tutor.id, acepta_diferidas=False)
    cuerpo = {"habilidad_id": str(habilidad.id), "mensaje": "Un enchufe suelta chispas"}

    respuesta = cliente_db.post("/solicitudes", json=cuerpo, headers=cabecera(aprendiz))
    assert respuesta.status_code == 409
    assert "no recibe solicitudes" in respuesta.json()["detail"]

    db_prueba.add(Bloqueo(bloqueador_id=tutor.id, bloqueado_id=aprendiz.id))
    db_prueba.flush()
    respuesta = cliente_db.post("/solicitudes", json=cuerpo, headers=cabecera(aprendiz))
    assert respuesta.status_code == 403