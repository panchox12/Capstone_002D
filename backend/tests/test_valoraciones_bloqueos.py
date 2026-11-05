"""Pruebas de las valoraciones, el promedio del perfil y los bloqueos."""
 
from decimal import Decimal
 
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
 
from app.modelos.perfil import PerfilPublico
from app.servicios import bloqueos, buscador, sesiones, valoraciones
from app.servicios.buscador import Modo
from tests.test_buscador import _tutor, catalogo  # noqa: F401
from tests.test_sesiones import _conectar_ambos, aprendiz, sala, sesion, tutor  # noqa: F401
from tests.utilidades import cabecera, crear_usuario
 
pytestmark = pytest.mark.usefixtures("parametros_iniciales")
 
 
@pytest.fixture()
def terminada(db_prueba: Session, sesion, aprendiz, tutor):
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    sesiones.terminar(db_prueba, sesion, "prueba")
    return sesion
 
 
# ---------------------------------------------------------------------------
# Valoraciones
# ---------------------------------------------------------------------------
 
 
def test_el_aprendiz_valora_al_tutor_y_sube_su_promedio(db_prueba: Session, terminada, aprendiz, tutor) -> None:
    valoracion = valoraciones.valorar(db_prueba, aprendiz.id, terminada.id, 5, "  Explica muy claro  ")
 
    perfil = db_prueba.get(PerfilPublico, tutor.id)
    assert valoracion.evaluado_id == tutor.id
    assert valoracion.comentario == "Explica muy claro"
    assert (perfil.reputacion_promedio, perfil.total_evaluaciones) == (Decimal("5.00"), 1)
 
 
def test_el_promedio_se_acumula_con_dos_decimales(db_prueba: Session, terminada, aprendiz, tutor) -> None:
    perfil = db_prueba.get(PerfilPublico, tutor.id) or PerfilPublico(usuario_id=tutor.id)
    perfil.reputacion_promedio = Decimal("4.00")
    perfil.total_evaluaciones = 2
    db_prueba.add(perfil)
    db_prueba.flush()
 
    valoraciones.valorar(db_prueba, aprendiz.id, terminada.id, 3, None)
 
    assert (perfil.reputacion_promedio, perfil.total_evaluaciones) == (Decimal("3.67"), 3)
 
 
def test_los_dos_se_pueden_valorar(db_prueba: Session, terminada, aprendiz, tutor) -> None:
    valoraciones.valorar(db_prueba, aprendiz.id, terminada.id, 5, None)
    de_tutor = valoraciones.valorar(db_prueba, tutor.id, terminada.id, 4, None)
 
    assert de_tutor.evaluado_id == aprendiz.id
 
 
def test_cada_uno_valora_una_sola_vez(db_prueba: Session, terminada, aprendiz) -> None:
    valoraciones.valorar(db_prueba, aprendiz.id, terminada.id, 5, None)
 
    with pytest.raises(valoraciones.ValoracionDuplicada):
        valoraciones.valorar(db_prueba, aprendiz.id, terminada.id, 1, None)
 
 
def test_no_se_valora_una_sesion_que_no_ocurrio(db_prueba: Session, sesion, aprendiz, sala) -> None:
    with pytest.raises(valoraciones.SesionNoValorable):
        valoraciones.valorar(db_prueba, aprendiz.id, sesion.id, 5, None)
 
    sesiones.terminar_por_participante(db_prueba, sala, aprendiz.id, sesion.id)
    with pytest.raises(valoraciones.SesionNoValorable):
        valoraciones.valorar(db_prueba, aprendiz.id, sesion.id, 5, None)
 
 
def test_valorar_por_la_api(cliente_db: TestClient, terminada, aprendiz) -> None:
    antes = cliente_db.get(f"/valoraciones/sesion/{terminada.id}", headers=cabecera(aprendiz)).json()
    creada = cliente_db.post(
        "/valoraciones", json={"sesion_id": str(terminada.id), "estrellas": 4}, headers=cabecera(aprendiz)
    )
    fuera_de_rango = cliente_db.post(
        "/valoraciones", json={"sesion_id": str(terminada.id), "estrellas": 6}, headers=cabecera(aprendiz)
    )
    repetida = cliente_db.post(
        "/valoraciones", json={"sesion_id": str(terminada.id), "estrellas": 4}, headers=cabecera(aprendiz)
    )
    despues = cliente_db.get(f"/valoraciones/sesion/{terminada.id}", headers=cabecera(aprendiz)).json()
 
    assert antes == {"valorada": False, "valoracion": None}
    assert creada.status_code == 201
    assert fuera_de_rango.status_code == 422
    assert repetida.status_code == 409
    assert despues["valorada"] is True
    assert despues["valoracion"]["estrellas"] == 4
 
 
# ---------------------------------------------------------------------------
# Bloqueos
# ---------------------------------------------------------------------------
 
 
def test_bloquear_dos_veces_no_duplica(db_prueba: Session) -> None:
    yo, otro = crear_usuario(db_prueba), crear_usuario(db_prueba)
    bloqueos.bloquear(db_prueba, yo.id, otro.id)
    bloqueos.bloquear(db_prueba, yo.id, otro.id)
 
    assert len(bloqueos.listar(db_prueba, yo.id)) == 1
    assert bloqueos.existe_entre(db_prueba, otro.id, yo.id)
 
 
def test_no_se_bloquea_a_si_mismo(db_prueba: Session) -> None:
    yo = crear_usuario(db_prueba)
 
    with pytest.raises(bloqueos.BloqueoAPropio):
        bloqueos.bloquear(db_prueba, yo.id, yo.id)
 
 
@pytest.mark.parametrize("quien_bloquea", ["aprendiz", "tutor"])
def test_un_bloqueo_saca_al_otro_del_buscador(
    db_prueba: Session, redis_falso, catalogo, aprendiz, quien_bloquea
) -> None:
    rodrigo = _tutor(db_prueba, catalogo["algebra"])
    otro = _tutor(db_prueba, catalogo["algebra"], nombre="Camila Torres")
    uno, dos = (aprendiz, rodrigo) if quien_bloquea == "aprendiz" else (rodrigo, aprendiz)
    bloqueos.bloquear(db_prueba, uno.id, dos.id)
 
    _, resultados = buscador.buscar(db_prueba, redis_falso, aprendiz.id, "algebra", Modo.LEXICO)
 
    assert [fila["tutor_id"] for fila in resultados] == [otro.id]
 
 
def test_al_desbloquear_vuelve_a_aparecer(db_prueba: Session, redis_falso, catalogo, aprendiz) -> None:
    rodrigo = _tutor(db_prueba, catalogo["algebra"])
    bloqueos.bloquear(db_prueba, aprendiz.id, rodrigo.id)
    bloqueos.desbloquear(db_prueba, aprendiz.id, rodrigo.id)
 
    _, resultados = buscador.buscar(db_prueba, redis_falso, aprendiz.id, "algebra", Modo.LEXICO)
 
    assert [fila["tutor_id"] for fila in resultados] == [rodrigo.id]
 
 
def test_bloqueos_por_la_api(cliente_db: TestClient, db_prueba: Session) -> None:
    yo = crear_usuario(db_prueba)
    otro = crear_usuario(db_prueba, nombre="Diego Contreras")
 
    assert cliente_db.post("/bloqueos", json={"usuario_id": str(otro.id)}, headers=cabecera(yo)).status_code == 204
    assert cliente_db.post("/bloqueos", json={"usuario_id": str(yo.id)}, headers=cabecera(yo)).status_code == 422
    lista = cliente_db.get("/bloqueos", headers=cabecera(yo)).json()
    assert [fila["nombre_visible"] for fila in lista] == ["Diego Contreras"]
 
    assert cliente_db.delete(f"/bloqueos/{otro.id}", headers=cabecera(yo)).status_code == 204
    assert cliente_db.get("/bloqueos", headers=cabecera(yo)).json() == []