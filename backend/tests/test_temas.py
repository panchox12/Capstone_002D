"""Pruebas del catalogo de temas."""
 
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
 
from app.modelos.tema import EstadoTema, Tema
from app.servicios import temas as servicio
 
 
def _rama(db: Session) -> tuple[Tema, Tema, Tema]:
    """Crea Ciencias exactas > Matematicas > Algebra."""
    raiz = servicio.crear(db, "Ciencias exactas")
    grupo = servicio.crear(db, "Matematicas", raiz.id)
    hoja = servicio.crear(db, "Algebra", grupo.id)
    return raiz, grupo, hoja
 
 
def test_el_nivel_se_calcula_desde_el_padre(db_prueba: Session) -> None:
    raiz, grupo, hoja = _rama(db_prueba)
 
    assert (raiz.nivel, grupo.nivel, hoja.nivel) == (1, 2, 3)
 
 
def test_no_se_puede_crear_un_cuarto_nivel(db_prueba: Session) -> None:
    _, _, hoja = _rama(db_prueba)
 
    with pytest.raises(servicio.NivelMaximoAlcanzado):
        servicio.crear(db_prueba, "Ecuaciones", hoja.id)
 
 
def test_el_padre_tiene_que_existir(db_prueba: Session) -> None:
    with pytest.raises(servicio.TemaNoExiste):
        servicio.crear(db_prueba, "Huerfano", 999999)
 
 
def test_no_se_repite_un_nombre_bajo_el_mismo_padre(db_prueba: Session) -> None:
    _, grupo, _ = _rama(db_prueba)
 
    with pytest.raises(IntegrityError):
        with db_prueba.begin_nested():
            servicio.crear(db_prueba, "Algebra", grupo.id)
 
 
def test_no_se_repite_un_tema_raiz(db_prueba: Session) -> None:
    _rama(db_prueba)
 
    with pytest.raises(IntegrityError):
        with db_prueba.begin_nested():
            servicio.crear(db_prueba, "Ciencias exactas")
 
 
def test_un_nombre_puede_repetirse_bajo_padres_distintos(db_prueba: Session) -> None:
    raiz = servicio.crear(db_prueba, "Tecnologia")
    python = servicio.crear(db_prueba, "Python", raiz.id)
    excel = servicio.crear(db_prueba, "Excel", raiz.id)
 
    servicio.crear(db_prueba, "Nivel basico", python.id)
    servicio.crear(db_prueba, "Nivel basico", excel.id)
 
 
def test_el_semillero_no_duplica_si_se_corre_dos_veces(db_prueba: Session) -> None:
    primero = servicio.obtener_o_crear(db_prueba, "Oficios")
    segundo = servicio.obtener_o_crear(db_prueba, "Oficios")
 
    assert primero.id == segundo.id
 
 
def test_el_arbol_anida_los_temas_y_oculta_los_inactivos(db_prueba: Session) -> None:
    _, grupo, _ = _rama(db_prueba)
    fisica = servicio.crear(db_prueba, "Fisica", grupo.tema_padre_id)
    servicio.crear(db_prueba, "Mecanica", fisica.id)
    fisica.estado = EstadoTema.INACTIVO
    db_prueba.flush()
 
    arbol = servicio.arbol(db_prueba)
 
    assert [nodo["nombre"] for nodo in arbol] == ["Ciencias exactas"]
    hijos = arbol[0]["hijos"]
    assert [nodo["nombre"] for nodo in hijos] == ["Matematicas"]
    assert hijos[0]["hijos"][0]["nombre"] == "Algebra"
 
 
def test_el_catalogo_es_publico(cliente_db: TestClient, db_prueba: Session) -> None:
    _rama(db_prueba)
 
    respuesta = cliente_db.get("/temas")
 
    assert respuesta.status_code == 200
    assert respuesta.json()[0]["hijos"][0]["hijos"][0]["nombre"] == "Algebra"