"""Pruebas de las grabaciones: inicio, aviso de termino, borrado a las 24 horas y acceso de soporte.

LiveKit y S3 se reemplazan por objetos falsos; la llamada real a LiveKit se
revisa armando el pedido con un cliente falso, y S3 con Stubber de boto3.
"""

import json
from datetime import timedelta

import boto3
import pytest
from botocore.stub import Stubber
from fastapi.testclient import TestClient
from livekit import api
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.main import app
from app.modelos.grabacion import AccesoGrabacion, EstadoGrabacion, Grabacion
from app.modelos.moderacion import MotivoReporte
from app.modelos.sesion import EstadoSesion
from app.modelos.usuario import RolUsuario
from app.servicios import grabaciones, reportes, sesiones, tokens
from app.servicios.almacen import AlmacenS3, obtener_almacen
from app.servicios.sala import EventoSala, SalaLiveKit, obtener_sala
from tests.test_sala_livekit import LLAVE, SECRETO, _firmar
from tests.test_sesiones import FIRMA_VALIDA, SalaFalsa, _aviso, _conectar_ambos, aprendiz, sesion, tutor  # noqa: F401
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


class SalaQueGraba(SalaFalsa):
    def __init__(self, falla: bool = False):
        super().__init__()
        self.falla = falla
        self.grabaciones = []

    def iniciar_grabacion(self, nombre_sala: str, clave_archivo: str) -> str:
        if self.falla:
            raise RuntimeError("LiveKit no responde")
        self.grabaciones.append((nombre_sala, clave_archivo))
        return f"EG_{len(self.grabaciones)}"

    def leer_evento(self, cuerpo: str, autorizacion: str) -> EventoSala:
        evento = super().leer_evento(cuerpo, autorizacion)
        datos = json.loads(cuerpo)
        return EventoSala(
            tipo=evento.tipo,
            sala=evento.sala,
            identidad=evento.identidad,
            egress_id=datos.get("egress_id"),
            grabacion_completa=datos.get("completa", False),
        )


class AlmacenFalso:
    def __init__(self):
        self.borrados = []

    def enlace_temporal(self, clave: str) -> str:
        return f"https://bucket.s3.amazonaws.com/{clave}?firma=temporal"

    def borrar(self, clave: str) -> None:
        self.borrados.append(clave)


@pytest.fixture(autouse=True)
def grabacion_activa(monkeypatch):
    monkeypatch.setattr(configuracion, "grabacion_activa", True)


@pytest.fixture()
def sala():
    falsa = SalaQueGraba()
    app.dependency_overrides[obtener_sala] = lambda: falsa
    yield falsa
    app.dependency_overrides.pop(obtener_sala, None)


@pytest.fixture()
def almacen():
    falso = AlmacenFalso()
    app.dependency_overrides[obtener_almacen] = lambda: falso
    yield falso
    app.dependency_overrides.pop(obtener_almacen, None)


@pytest.fixture()
def soporte(db_prueba: Session):
    usuario = crear_usuario(db_prueba, nombre="Equipo Soporte")
    usuario.rol = RolUsuario.SOPORTE
    db_prueba.flush()
    return usuario


def _avisar_por_api(cliente: TestClient, tipo: str, sesion, usuario=None, **extra) -> None:
    cuerpo = {"tipo": tipo, "sala": sesion.nombre_sala, **extra}
    if usuario is not None:
        cuerpo["identidad"] = str(usuario.id)
    respuesta = cliente.post(
        "/sesiones/webhook", content=json.dumps(cuerpo), headers={"Authorization": FIRMA_VALIDA}
    )
    assert respuesta.status_code == 204


def _grabacion(db: Session, sesion) -> Grabacion | None:
    return grabaciones.de_sesion(db, sesion.id)


def _grabada(db: Session, sesion, aprendiz, tutor, sala) -> Grabacion:
    _conectar_ambos(db, sesion, aprendiz, tutor)
    return grabaciones.iniciar(db, sala, sesion)


# ---------------------------------------------------------------------------
# Inicio y termino
# ---------------------------------------------------------------------------


def test_cuando_se_conectan_los_dos_empieza_la_grabacion(
    db_prueba: Session, cliente_db: TestClient, sala, sesion, aprendiz, tutor
) -> None:
    _avisar_por_api(cliente_db, "participant_joined", sesion, aprendiz)
    assert _grabacion(db_prueba, sesion) is None

    _avisar_por_api(cliente_db, "participant_joined", sesion, tutor)

    grabacion = _grabacion(db_prueba, sesion)
    assert grabacion.estado == EstadoGrabacion.GRABANDO
    assert grabacion.egress_id == "EG_1"
    assert sala.grabaciones == [(sesion.nombre_sala, f"grabaciones/{sesion.id}.mp4")]


def test_reconectarse_no_abre_otra_grabacion(
    db_prueba: Session, cliente_db: TestClient, sala, sesion, aprendiz, tutor
) -> None:
    _avisar_por_api(cliente_db, "participant_joined", sesion, aprendiz)
    _avisar_por_api(cliente_db, "participant_joined", sesion, tutor)
    _avisar_por_api(cliente_db, "participant_left", sesion, tutor)
    _avisar_por_api(cliente_db, "participant_joined", sesion, tutor)

    assert len(sala.grabaciones) == 1


def test_con_la_grabacion_apagada_no_se_graba(db_prueba: Session, monkeypatch, sala, sesion, aprendiz, tutor) -> None:
    monkeypatch.setattr(configuracion, "grabacion_activa", False)

    assert _grabada(db_prueba, sesion, aprendiz, tutor, sala) is None
    assert sala.grabaciones == []


def test_sin_consentimiento_de_alguno_no_se_graba(db_prueba: Session, sala, sesion, aprendiz, tutor) -> None:
    tutor.consentimiento_grabacion = False

    assert _grabada(db_prueba, sesion, aprendiz, tutor, sala) is None


def test_si_livekit_no_puede_grabar_la_sesion_sigue(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    grabacion = _grabada(db_prueba, sesion, aprendiz, tutor, SalaQueGraba(falla=True))

    assert grabacion.estado == EstadoGrabacion.FALLIDA
    assert sesion.estado == EstadoSesion.EN_CURSO


@pytest.mark.parametrize(("completa", "estado"), [(True, EstadoGrabacion.DISPONIBLE), (False, EstadoGrabacion.FALLIDA)])
def test_el_aviso_de_termino_deja_la_grabacion_disponible_o_fallida(
    db_prueba: Session, cliente_db: TestClient, sala, sesion, aprendiz, tutor, completa, estado
) -> None:
    grabacion = _grabada(db_prueba, sesion, aprendiz, tutor, sala)

    _avisar_por_api(cliente_db, "egress_ended", sesion, egress_id=grabacion.egress_id, completa=completa)

    assert grabacion.estado == estado


def test_al_cerrar_la_sesion_la_grabacion_vence_en_24_horas(db_prueba: Session, sala, sesion, aprendiz, tutor) -> None:
    grabacion = _grabada(db_prueba, sesion, aprendiz, tutor, sala)

    sesiones.terminar(db_prueba, sesion, "prueba")

    assert grabacion.fecha_expiracion - sesion.fecha_cierre == timedelta(hours=24)


# ---------------------------------------------------------------------------
# Borrado
# ---------------------------------------------------------------------------


def _vencida(db: Session, sesion, aprendiz, tutor, sala) -> Grabacion:
    grabacion = _grabada(db, sesion, aprendiz, tutor, sala)
    grabacion.estado = EstadoGrabacion.DISPONIBLE
    sesiones.terminar(db, sesion, "prueba")
    grabacion.fecha_expiracion = tokens.ahora() - timedelta(seconds=1)
    db.flush()
    return grabacion


def test_vencida_se_borra_del_bucket(db_prueba: Session, sala, almacen, sesion, aprendiz, tutor) -> None:
    grabacion = _vencida(db_prueba, sesion, aprendiz, tutor, sala)

    assert grabaciones.borrar_vencidas(db_prueba, almacen) == 1
    assert grabacion.estado == EstadoGrabacion.BORRADA
    assert almacen.borrados == [grabacion.clave_archivo]


def test_antes_de_vencer_no_se_borra(db_prueba: Session, sala, almacen, sesion, aprendiz, tutor) -> None:
    _grabada(db_prueba, sesion, aprendiz, tutor, sala)
    sesiones.terminar(db_prueba, sesion, "prueba")

    assert grabaciones.borrar_vencidas(db_prueba, almacen) == 0


def test_con_un_reporte_abierto_se_conserva_hasta_resolverlo(
    db_prueba: Session, sala, almacen, soporte, sesion, aprendiz, tutor
) -> None:
    grabacion = _vencida(db_prueba, sesion, aprendiz, tutor, sala)
    reporte = reportes.crear(db_prueba, aprendiz.id, sesion.id, MotivoReporte.CONDUCTA, "Fue grosero todo el rato")

    assert grabaciones.borrar_vencidas(db_prueba, almacen) == 0

    reportes.resolver(db_prueba, soporte.id, reporte.id, False, "No se observa la conducta")
    assert grabaciones.borrar_vencidas(db_prueba, almacen) == 1
    assert grabacion.estado == EstadoGrabacion.BORRADA


# ---------------------------------------------------------------------------
# Acceso de soporte
# ---------------------------------------------------------------------------


def test_soporte_abre_la_grabacion_y_queda_anotado(
    db_prueba: Session, cliente_db: TestClient, sala, almacen, soporte, sesion, aprendiz, tutor
) -> None:
    grabacion = _grabada(db_prueba, sesion, aprendiz, tutor, sala)
    grabacion.estado = EstadoGrabacion.DISPONIBLE
    sesiones.terminar(db_prueba, sesion, "prueba")
    reporte = reportes.crear(db_prueba, aprendiz.id, sesion.id, MotivoReporte.CONDUCTA, "Fue grosero todo el rato")

    detalle = cliente_db.get(f"/soporte/reportes/{reporte.id}", headers=cabecera(soporte)).json()
    assert detalle["grabacion"] == "disponible"

    enlace = cliente_db.post(f"/soporte/reportes/{reporte.id}/grabacion", headers=cabecera(soporte))
    assert enlace.status_code == 200
    assert grabacion.clave_archivo in enlace.json()["url"]

    (acceso,) = db_prueba.execute(select(AccesoGrabacion)).scalars()
    assert (acceso.usuario_id, acceso.reporte_id) == (soporte.id, reporte.id)
    bitacora = cliente_db.get(f"/soporte/reportes/{reporte.id}/accesos", headers=cabecera(soporte)).json()
    assert [fila["soporte"] for fila in bitacora] == ["Equipo Soporte"]


def test_sin_reporte_abierto_no_se_abre(
    db_prueba: Session, cliente_db: TestClient, sala, almacen, soporte, sesion, aprendiz, tutor
) -> None:
    grabacion = _grabada(db_prueba, sesion, aprendiz, tutor, sala)
    grabacion.estado = EstadoGrabacion.DISPONIBLE
    sesiones.terminar(db_prueba, sesion, "prueba")
    reporte = reportes.crear(db_prueba, aprendiz.id, sesion.id, MotivoReporte.CONDUCTA, "Fue grosero todo el rato")
    reportes.resolver(db_prueba, soporte.id, reporte.id, False, "No se observa la conducta")

    respuesta = cliente_db.post(f"/soporte/reportes/{reporte.id}/grabacion", headers=cabecera(soporte))

    assert respuesta.status_code == 409


def test_los_participantes_no_abren_la_grabacion(
    db_prueba: Session, cliente_db: TestClient, sala, almacen, sesion, aprendiz, tutor
) -> None:
    _grabada(db_prueba, sesion, aprendiz, tutor, sala)
    sesiones.terminar(db_prueba, sesion, "prueba")
    reporte = reportes.crear(db_prueba, aprendiz.id, sesion.id, MotivoReporte.CONDUCTA, "Fue grosero todo el rato")

    respuesta = cliente_db.post(f"/soporte/reportes/{reporte.id}/grabacion", headers=cabecera(aprendiz))

    assert respuesta.status_code == 403


# ---------------------------------------------------------------------------
# Conexion real con LiveKit y S3, sin red
# ---------------------------------------------------------------------------


def test_el_pedido_a_livekit_graba_en_mp4_hacia_el_bucket(monkeypatch) -> None:
    monkeypatch.setattr(configuracion, "grabacion_bucket", "cachai-grabaciones-prueba")
    monkeypatch.setattr(configuracion, "aws_region", "us-east-2")
    pedidos = []

    class EgressFalso:
        async def start_room_composite_egress(self, pedido):
            pedidos.append(pedido)
            return api.EgressInfo(egress_id="EG_real")

    class ClienteFalso:
        egress = EgressFalso()

        def __init__(self, *args):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(api, "LiveKitAPI", ClienteFalso)

    egress_id = SalaLiveKit("wss://x.livekit.cloud", LLAVE, SECRETO).iniciar_grabacion("cachai-1", "grabaciones/1.mp4")

    (pedido,) = pedidos
    salida = pedido.file_outputs[0]
    assert egress_id == "EG_real"
    assert pedido.room_name == "cachai-1"
    assert salida.file_type == api.EncodedFileType.MP4
    assert salida.filepath == "grabaciones/1.mp4"
    assert (salida.s3.bucket, salida.s3.region) == ("cachai-grabaciones-prueba", "us-east-2")


def test_lee_el_aviso_de_termino_de_grabacion() -> None:
    cuerpo = json.dumps(
        {"event": "egress_ended", "egressInfo": {"egressId": "EG_1", "roomName": "cachai-1", "status": "EGRESS_COMPLETE"}}
    )

    evento = SalaLiveKit("wss://x.livekit.cloud", LLAVE, SECRETO).leer_evento(cuerpo, _firmar(cuerpo))

    assert (evento.tipo, evento.sala, evento.egress_id, evento.grabacion_completa) == (
        "egress_ended",
        "cachai-1",
        "EG_1",
        True,
    )


def test_el_almacen_borra_y_firma_enlaces_en_s3() -> None:
    cliente = boto3.client("s3", region_name="us-east-2", aws_access_key_id="x", aws_secret_access_key="x")
    almacen = AlmacenS3(cliente, "cachai-grabaciones-prueba")

    with Stubber(cliente) as stub:
        stub.add_response("delete_object", {}, {"Bucket": "cachai-grabaciones-prueba", "Key": "grabaciones/1.mp4"})
        almacen.borrar("grabaciones/1.mp4")
        stub.assert_no_pending_responses()

    enlace = almacen.enlace_temporal("grabaciones/1.mp4")
    assert "cachai-grabaciones-prueba" in enlace and "grabaciones/1.mp4" in enlace and "Expires=600" in enlace