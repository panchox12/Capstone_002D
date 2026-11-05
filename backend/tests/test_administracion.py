"""Pruebas del panel del administrador: parametros editables e indicadores de la economia."""
 
from datetime import timedelta
 
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
 
from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.usuario import RolUsuario
from app.servicios import indicadores, parametros, tienda, tokens
from tests.utilidades import cabecera, crear_usuario
 
pytestmark = pytest.mark.usefixtures("parametros_iniciales")
 
 
@pytest.fixture()
def admin(db_prueba: Session):
    usuario = crear_usuario(db_prueba, nombre="Administracion")
    usuario.rol = RolUsuario.ADMINISTRADOR
    db_prueba.flush()
    return usuario
 
 
def test_los_indicadores_salen_de_los_movimientos(db_prueba: Session) -> None:
    ana = crear_usuario(db_prueba)
    crear_usuario(db_prueba)
    tokens.otorgar(db_prueba, ana.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    tienda.comprar(db_prueba, ana.id, "popular")
    tokens.retener(db_prueba, ana.id, 3)
    vencido = tokens.otorgar(db_prueba, ana.id, 5, TipoSaldo.GRATIS, OrigenLote.VIDEO, 7)
    vencido.fecha_vencimiento = tokens.ahora() - timedelta(days=1)
    db_prueba.flush()
 
    datos = indicadores.calcular(db_prueba)
 
    assert datos["masa_circulante"] == 20
    assert datos["tokens_retenidos"] == 3
    assert datos["tokens_entregados"] == 28
    assert datos["tokens_consumidos"] == 3
    assert datos["tokens_vencidos"] == 5
    assert datos["velocidad"] == 0.15
    assert datos["tasa_caducidad"] == round(5 / 28, 4)
    # Los 3 retenidos salieron del lote gratis, que vence antes que el comprado.
    assert datos["cobertura_gratuita"] == 1.0
    assert datos["conversion"] == 0.5
 
 
def test_sin_movimientos_los_indicadores_son_cero(db_prueba: Session) -> None:
    datos = indicadores.calcular(db_prueba)
 
    assert datos["velocidad"] == datos["tasa_caducidad"] == datos["conversion"] == 0.0
 
 
def test_el_panel_es_solo_del_administrador(cliente_db: TestClient, db_prueba: Session, admin) -> None:
    soporte = crear_usuario(db_prueba)
    soporte.rol = RolUsuario.SOPORTE
    db_prueba.flush()
 
    assert cliente_db.get("/admin/indicadores", headers=cabecera(soporte)).status_code == 403
    assert cliente_db.get("/admin/indicadores", headers=cabecera(admin)).status_code == 200
 
 
def test_el_administrador_cambia_un_parametro_sin_tocar_codigo(
    cliente_db: TestClient, db_prueba: Session, admin
) -> None:
    lista = cliente_db.get("/admin/parametros", headers=cabecera(admin)).json()
    assert "tokens_gratis_semanales" in [fila["nombre"] for fila in lista]
 
    cambio = cliente_db.put(
        "/admin/parametros/tokens_gratis_semanales", json={"valor": 12}, headers=cabecera(admin)
    )
 
    assert cambio.status_code == 200
    assert parametros.obtener_entero(db_prueba, "tokens_gratis_semanales") == 12
 
 
def test_no_se_aceptan_valores_negativos_ni_parametros_inventados(cliente_db: TestClient, admin) -> None:
    negativo = cliente_db.put("/admin/parametros/tope_videos_por_dia", json={"valor": -1}, headers=cabecera(admin))
    inventado = cliente_db.put("/admin/parametros/no_existe", json={"valor": 1}, headers=cabecera(admin))
 
    assert negativo.status_code == 422
    assert inventado.status_code == 404