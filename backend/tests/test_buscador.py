"""Pruebas del servicio y endpoints del buscador de habilidades."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos.habilidad import EstadoHabilidad
from app.servicios import buscador, habilidades, temas
from tests.utilidades import crear_usuario


@pytest.fixture
def datos_busqueda(db_prueba: Session, parametros_iniciales):
    """Crea un escenario base con usuarios, temas y habilidades con embeddings ficticios."""
    _ = parametros_iniciales
    tutor_a = crear_usuario(db_prueba, nombre="Rodrigo Salas")
    tutor_b = crear_usuario(db_prueba, nombre="Ana Lopez")

    # Nivel 1 (Raíz)
    raiz = temas.crear(db_prueba, "Tecnologia")
    # Nivel 2 (Subcategoría)
    sub_dev = temas.crear(db_prueba, "Desarrollo de Software", tema_padre_id=raiz.id)
    # Nivel 3 (NIVEL_MAXIMO / Hoja)
    tema_python = temas.crear(db_prueba, "Programacion Python", tema_padre_id=sub_dev.id)
    tema_react = temas.crear(db_prueba, "Desarrollo Frontend React", tema_padre_id=sub_dev.id)

    # Creamos dos vectores normalizados unitarios de 384 dimensiones
    vec_python = [0.0] * 384
    vec_python[0] = 1.0

    vec_react = [0.0] * 384
    vec_react[1] = 1.0

    hab_python = habilidades.publicar(db_prueba, tutor_a.id, tema_python.id, 5)
    hab_python.embedding = vec_python

    hab_react = habilidades.publicar(db_prueba, tutor_b.id, tema_react.id, 4)
    hab_react.embedding = vec_react

    db_prueba.commit()
    db_prueba.refresh(hab_python)
    db_prueba.refresh(hab_react)

    return {
        "tutor_a": tutor_a,
        "tutor_b": tutor_b,
        "hab_python": hab_python,
        "hab_react": hab_react,
        "vec_python": vec_python,
        "vec_react": vec_react,
    }
def test_busqueda_lexica_por_texto(db_prueba: Session, cliente_db: TestClient, datos_busqueda):
    respuesta = cliente_db.get("/buscador/habilidades?q=python")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["tema"]["nombre"] == "Programacion Python"
    assert datos[0]["usuario"]["nombre_visible"] == "Rodrigo Salas"


def test_busqueda_lexica_vacia_trae_todas(cliente_db: TestClient, datos_busqueda):
    respuesta = cliente_db.get("/buscador/habilidades")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 2


def test_busqueda_lexica_sin_coincidencias(cliente_db: TestClient, datos_busqueda):
    respuesta = cliente_db.get("/buscador/habilidades?q=astronomia")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_busqueda_semantica_ordena_por_cercania_vectorial(db_prueba: Session, datos_busqueda):
    # Vector de consulta idéntico al de Python
    consulta_vec = [0.0] * 384
    consulta_vec[0] = 1.0

    resultados = buscador.buscar_habilidades(db_prueba, embedding=consulta_vec)

    assert len(resultados) == 2
    # El más cercano por distancia coseno debe ser la habilidad de Python (distancia 0)
    assert resultados[0].id == datos_busqueda["hab_python"].id
    assert resultados[1].id == datos_busqueda["hab_react"].id


def test_no_retorna_habilidades_pausadas(db_prueba: Session, cliente_db: TestClient, datos_busqueda):
    datos_busqueda["hab_python"].estado = EstadoHabilidad.PAUSADA
    db_prueba.commit()

    respuesta = cliente_db.get("/buscador/habilidades?q=python")

    assert respuesta.status_code == 200
    assert respuesta.json() == []