"""Pruebas de los avisos de la campana y de los correos.

El correo se reemplaza por un buzon en memoria; SES se prueba con un cliente
de boto3 con respuestas preparadas (Stubber), sin red.
"""

import boto3
import pytest
from botocore.stub import Stubber
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.moderacion import MotivoReporte, TipoSancion
from app.modelos.notificacion import Notificacion
from app.modelos.usuario import RolUsuario
from app.servicios import correo, habilidades, notificaciones, presencia, reportes, sesiones, solicitudes, temas, tokens
from tests.test_sesiones import _conectar_ambos
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


class Buzon:
    def __init__(self):
        self.enviados = []

    def enviar(self, destinatario: str, asunto: str, texto: str) -> None:
        self.enviados.append((destinatario, asunto, texto))


@pytest.fixture()
def buzon(monkeypatch):
    falso = Buzon()
    monkeypatch.setattr(correo, "obtener_proveedor", lambda: falso)
    return falso


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
    raiz = temas.crear(db_prueba, "Ciencias exactas")
    grupo = temas.crear(db_prueba, "Matematicas", raiz.id)
    algebra = temas.crear(db_prueba, "Algebra", grupo.id)
    return habilidades.publicar(db_prueba, tutor.id, algebra.id, 3)


def _avisos(db: Session, usuario) -> list[Notificacion]:
    return list(db.execute(select(Notificacion).where(Notificacion.usuario_id == usuario.id)).scalars())


# ---------------------------------------------------------------------------
# Proveedores de correo
# ---------------------------------------------------------------------------


def test_en_desarrollo_el_correo_se_imprime(capsys) -> None:
    correo.CorreoConsola().enviar("ana@duoc.cl", "Hola", "Texto de prueba")

    salida = capsys.readouterr().out
    assert "CORREO PARA ana@duoc.cl: Hola" in salida
    assert "Texto de prueba" in salida


def test_ses_recibe_remitente_destinatario_y_texto() -> None:
    cliente = boto3.client("sesv2", region_name="us-east-2", aws_access_key_id="x", aws_secret_access_key="x")
    esperado = {
        "FromEmailAddress": "cachai@duoc.cl",
        "Destination": {"ToAddresses": ["ana@duoc.cl"]},
        "Content": {
            "Simple": {
                "Subject": {"Data": "Hola", "Charset": "UTF-8"},
                "Body": {"Text": {"Data": "Texto", "Charset": "UTF-8"}},
            }
        },
    }
    with Stubber(cliente) as stub:
        stub.add_response("send_email", {"MessageId": "123"}, esperado)
        correo.CorreoSES(cliente, "cachai@duoc.cl").enviar("ana@duoc.cl", "Hola", "Texto")
        stub.assert_no_pending_responses()


def test_si_el_correo_falla_la_operacion_sigue(monkeypatch) -> None:
    class Roto:
        def enviar(self, *args):
            raise RuntimeError("SES no responde")

    monkeypatch.setattr(correo, "obtener_proveedor", lambda: Roto())

    assert correo.enviar("ana@duoc.cl", "Hola", "Texto") is False


# ---------------------------------------------------------------------------
# Avisos que generan los demas modulos
# ---------------------------------------------------------------------------


def test_avisar_guarda_el_aviso_y_si_se_pide_manda_correo(db_prueba: Session, buzon, tutor) -> None:
    notificaciones.avisar(db_prueba, tutor.id, "prueba", "Titulo", "Mensaje", "/solicitudes", por_correo=True)

    (aviso,) = _avisos(db_prueba, tutor)
    assert aviso.leida is False
    destinatario, asunto, texto = buzon.enviados[0]
    assert destinatario == tutor.correo
    assert asunto == "Cachai: Titulo"
    assert texto.endswith("/solicitudes")


def test_una_solicitud_en_vivo_avisa_al_tutor_sin_correo(
    db_prueba: Session, redis_falso, buzon, tutor, aprendiz, habilidad
) -> None:
    presencia.marcar_en_linea(redis_falso, tutor.id)

    solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")

    (aviso,) = _avisos(db_prueba, tutor)
    assert aviso.tipo == "solicitud_recibida"
    assert "Valentina Rojas" in aviso.mensaje and "Algebra" in aviso.mensaje
    assert buzon.enviados == []


def test_una_solicitud_diferida_tambien_llega_por_correo(
    db_prueba: Session, redis_falso, buzon, tutor, aprendiz, habilidad
) -> None:
    solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")

    assert [destinatario for destinatario, _, _ in buzon.enviados] == [tutor.correo]


def test_aceptar_avisa_al_aprendiz_con_el_enlace_a_la_sala(
    db_prueba: Session, redis_falso, buzon, tutor, aprendiz, habilidad
) -> None:
    presencia.marcar_en_linea(redis_falso, tutor.id)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")

    solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)

    (aviso,) = _avisos(db_prueba, aprendiz)
    assert aviso.tipo == "solicitud_aceptada"
    assert aviso.enlace.startswith("/sesiones/")


def test_rechazar_y_vencer_avisan_al_aprendiz(
    db_prueba: Session, redis_falso, buzon, tutor, aprendiz, habilidad
) -> None:
    presencia.marcar_en_linea(redis_falso, tutor.id)
    primera = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")
    solicitudes.rechazar(db_prueba, tutor.id, primera.id)
    segunda = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Otra duda")
    segunda.fecha_limite_respuesta = tokens.ahora()
    db_prueba.flush()
    solicitudes.vencer_atrasadas(db_prueba)

    assert sorted(a.tipo for a in _avisos(db_prueba, aprendiz)) == ["solicitud_rechazada", "solicitud_vencida"]


def test_la_sancion_llega_por_correo(db_prueba: Session, redis_falso, buzon, tutor, aprendiz, habilidad) -> None:
    presencia.marcar_en_linea(redis_falso, tutor.id)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")
    solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)
    sesion = db_prueba.execute(select(sesiones.Sesion).where(sesiones.Sesion.solicitud_id == solicitud.id)).scalar_one()
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    sesiones.terminar(db_prueba, sesion, "prueba")
    soporte = crear_usuario(db_prueba, nombre="Soporte")
    soporte.rol = RolUsuario.SOPORTE
    reporte = reportes.crear(db_prueba, aprendiz.id, sesion.id, MotivoReporte.CONDUCTA, "Fue grosero todo el rato")

    reportes.resolver(db_prueba, soporte.id, reporte.id, True, "Se comprobo la conducta", TipoSancion.TEMPORAL, 3)

    assert any(a.tipo == "reporte_resuelto" for a in _avisos(db_prueba, aprendiz))
    assert any(a.tipo == "sancion" for a in _avisos(db_prueba, tutor))
    assert tutor.correo in [destinatario for destinatario, _, _ in buzon.enviados]


def test_el_registro_manda_el_enlace_de_confirmacion(cliente_db: TestClient, buzon) -> None:
    cuerpo = {
        "correo": "nueva@duoc.cl",
        "contrasena": "clave12345",
        "nombre_visible": "Nueva Persona",
        "acepta_terminos": True,
        "consentimiento_grabacion": True,
    }

    assert cliente_db.post("/auth/registro", json=cuerpo).status_code == 201
    destinatario, _, texto = buzon.enviados[0]
    assert destinatario == "nueva@duoc.cl"
    assert "/confirmar/" in texto


# ---------------------------------------------------------------------------
# API de la campana
# ---------------------------------------------------------------------------


def test_la_campana_cuenta_y_marca_los_avisos(db_prueba: Session, cliente_db: TestClient, buzon, tutor) -> None:
    primero = notificaciones.avisar(db_prueba, tutor.id, "prueba", "Uno", "Primer aviso")
    notificaciones.avisar(db_prueba, tutor.id, "prueba", "Dos", "Segundo aviso")
    ajeno = notificaciones.avisar(db_prueba, crear_usuario(db_prueba).id, "prueba", "Ajeno", "No es tuyo")

    bandeja = cliente_db.get("/notificaciones", headers=cabecera(tutor)).json()
    assert bandeja["no_leidas"] == 2
    assert len(bandeja["avisos"]) == 2

    assert cliente_db.post(f"/notificaciones/{primero.id}/leida", headers=cabecera(tutor)).json()["leida"] is True
    assert cliente_db.post(f"/notificaciones/{ajeno.id}/leida", headers=cabecera(tutor)).status_code == 404
    assert cliente_db.get("/notificaciones", headers=cabecera(tutor)).json()["no_leidas"] == 1

    assert cliente_db.post("/notificaciones/leer-todas", headers=cabecera(tutor)).status_code == 204
    assert cliente_db.get("/notificaciones", headers=cabecera(tutor)).json()["no_leidas"] == 0