"""Pruebas del modelo: roles, reglas de las tablas nuevas y el script de roles."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencias import usuario_con_rol
from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.moderacion import Bloqueo, MotivoReporte, Reporte, Valoracion
from app.modelos.sesion import Sesion
from app.modelos.usuario import RolUsuario
from app.servicios import habilidades, presencia, solicitudes, temas, tokens
from scripts import asignar_rol
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


@pytest.fixture()
def pareja(db_prueba: Session, redis_falso):
    tutor = crear_usuario(db_prueba, nombre="Rodrigo Salas", verificado=True)
    aprendiz = crear_usuario(db_prueba, nombre="Valentina Rojas", verificado=True)
    presencia.marcar_en_linea(redis_falso, tutor.id)
    tokens.otorgar(db_prueba, aprendiz.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    raiz = temas.crear(db_prueba, "Ciencias exactas")
    grupo = temas.crear(db_prueba, "Matematicas", raiz.id)
    algebra = temas.crear(db_prueba, "Algebra", grupo.id)
    habilidad = habilidades.publicar(db_prueba, tutor.id, algebra.id, 3)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")
    solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)
    sesion = db_prueba.execute(select(Sesion).where(Sesion.solicitud_id == solicitud.id)).scalar_one()
    return tutor, aprendiz, sesion


def _guardar_con_error(db: Session, fila) -> None:
    # Usa un punto de guardado para que el error no deshaga el resto de la prueba.
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(fila)
        db.flush()


def test_toda_cuenta_nueva_parte_como_usuario(db_prueba: Session) -> None:
    assert crear_usuario(db_prueba).rol == RolUsuario.USUARIO


def test_la_api_informa_el_rol(cliente_db: TestClient, db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    usuario.rol = RolUsuario.SOPORTE
    db_prueba.flush()

    respuesta = cliente_db.get("/auth/yo", headers=cabecera(usuario))

    assert respuesta.json()["rol"] == "soporte"


def test_la_dependencia_de_rol_deja_pasar_solo_al_personal(db_prueba: Session) -> None:
    exigir = usuario_con_rol(RolUsuario.SOPORTE, RolUsuario.ADMINISTRADOR)
    comun = crear_usuario(db_prueba)
    soporte = crear_usuario(db_prueba)
    soporte.rol = RolUsuario.SOPORTE

    assert exigir(soporte) is soporte
    with pytest.raises(HTTPException) as error:
        exigir(comun)
    assert error.value.status_code == 403


def test_las_estrellas_van_de_1_a_5(db_prueba: Session, pareja) -> None:
    tutor, aprendiz, sesion = pareja
    _guardar_con_error(
        db_prueba, Valoracion(sesion_id=sesion.id, evaluador_id=aprendiz.id, evaluado_id=tutor.id, estrellas=6)
    )


def test_cada_participante_valora_una_sola_vez(db_prueba: Session, pareja) -> None:
    tutor, aprendiz, sesion = pareja
    db_prueba.add(Valoracion(sesion_id=sesion.id, evaluador_id=aprendiz.id, evaluado_id=tutor.id, estrellas=5))
    db_prueba.flush()

    _guardar_con_error(
        db_prueba, Valoracion(sesion_id=sesion.id, evaluador_id=aprendiz.id, evaluado_id=tutor.id, estrellas=4)
    )


def test_nadie_se_bloquea_a_si_mismo(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    _guardar_con_error(db_prueba, Bloqueo(bloqueador_id=usuario.id, bloqueado_id=usuario.id))


def test_los_reportes_reciben_folio_correlativo(db_prueba: Session, pareja) -> None:
    tutor, aprendiz, sesion = pareja
    primero = Reporte(
        sesion_id=sesion.id,
        reportante_id=aprendiz.id,
        reportado_id=tutor.id,
        motivo=MotivoReporte.INCUMPLIMIENTO,
        descripcion="No se conecto nunca a la sala",
    )
    segundo = Reporte(
        sesion_id=sesion.id,
        reportante_id=tutor.id,
        reportado_id=aprendiz.id,
        motivo=MotivoReporte.CONDUCTA,
        descripcion="Fue grosero durante la llamada",
    )
    db_prueba.add_all([primero, segundo])
    db_prueba.flush()

    assert primero.folio >= 1000
    assert segundo.folio == primero.folio + 1


def test_un_reporte_necesita_una_descripcion_minima(db_prueba: Session, pareja) -> None:
    tutor, aprendiz, sesion = pareja
    _guardar_con_error(
        db_prueba,
        Reporte(
            sesion_id=sesion.id,
            reportante_id=aprendiz.id,
            reportado_id=tutor.id,
            motivo=MotivoReporte.OTRO,
            descripcion="mal",
        ),
    )


class _SesionSinCommit:
    # Deja que el script use la base de pruebas sin confirmar ni cerrar la transaccion.
    def __init__(self, db: Session):
        self.db = db

    def execute(self, *args, **kwargs):
        return self.db.execute(*args, **kwargs)

    def commit(self) -> None:
        self.db.flush()

    def close(self) -> None:
        pass


def test_el_script_asigna_y_valida_el_rol(db_prueba: Session, monkeypatch) -> None:
    usuario = crear_usuario(db_prueba)
    monkeypatch.setattr(asignar_rol, "SesionLocal", lambda: _SesionSinCommit(db_prueba))

    assert "administrador" in asignar_rol.asignar(usuario.correo.upper(), "administrador")
    assert usuario.rol == RolUsuario.ADMINISTRADOR
    assert "Rol desconocido" in asignar_rol.asignar(usuario.correo, "jefe")
    assert "No existe" in asignar_rol.asignar("nadie@prueba.cl", "soporte")