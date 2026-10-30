"""Pruebas del buscador lexico y semantico.

Usan el proveedor de embeddings simulado: no descarga el modelo y da
siempre el mismo vector para el mismo texto.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos.embedding import EmbeddingTema
from app.modelos.habilidad import EstadoHabilidad
from app.modelos.perfil import PerfilPublico
from app.modelos.tema import EstadoTema
from app.modelos.usuario import EstadoCuenta
from app.servicios import buscador, embeddings, habilidades, presencia, temas
from app.servicios.buscador import Modo
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


@pytest.fixture()
def catalogo(db_prueba: Session) -> dict:
    oficios = temas.crear(db_prueba, "Oficios")
    electricidad = temas.crear(db_prueba, "Electricidad", oficios.id)
    exactas = temas.crear(db_prueba, "Ciencias exactas")
    matematicas = temas.crear(db_prueba, "Matemáticas", exactas.id)
    return {
        "enchufes": temas.crear(db_prueba, "Instalaciones eléctricas domiciliarias", electricidad.id),
        "algebra": temas.crear(db_prueba, "Álgebra", matematicas.id),
        "calculo": temas.crear(db_prueba, "Cálculo", matematicas.id),
    }


@pytest.fixture()
def aprendiz(db_prueba: Session):
    return crear_usuario(db_prueba, nombre="Valentina Rojas", verificado=True)


def _tutor(db: Session, tema, precio: int = 3, nombre: str = "Rodrigo Salas"):
    usuario = crear_usuario(db, nombre=nombre, verificado=True)
    habilidades.publicar(db, usuario.id, tema.id, precio)
    return usuario


# ---------------------------------------------------------------------------
# Normalizacion y temas lexicos
# ---------------------------------------------------------------------------


def test_normalizar_quita_tildes_y_mayusculas() -> None:
    assert embeddings.normalizar("Álgebra Lineal") == "algebra lineal"


def test_el_lexico_encuentra_el_tema_sin_importar_las_tildes(db_prueba: Session, catalogo) -> None:
    [(tema_id, puntaje)] = buscador.temas_lexicos(db_prueba, "duda de algebra")

    assert tema_id == catalogo["algebra"].id
    assert puntaje == 1.0


def test_el_lexico_tambien_busca_en_la_ruta_del_tema(db_prueba: Session, catalogo) -> None:
    encontrados = {tema_id for tema_id, _ in buscador.temas_lexicos(db_prueba, "matematicas")}

    assert encontrados == {catalogo["algebra"].id, catalogo["calculo"].id}


def test_las_palabras_vacias_no_cuentan(db_prueba: Session, catalogo) -> None:
    assert buscador.temas_lexicos(db_prueba, "tengo una duda") == []


def test_un_tema_con_padre_inactivo_no_se_ofrece(db_prueba: Session, catalogo) -> None:
    db_prueba.get(type(catalogo["algebra"]), catalogo["algebra"].tema_padre_id).estado = EstadoTema.INACTIVO

    assert buscador.temas_lexicos(db_prueba, "algebra") == []


# ---------------------------------------------------------------------------
# Embeddings y temas semanticos
# ---------------------------------------------------------------------------


def test_calcular_embeddings_solo_vectoriza_los_temas_de_nivel_3(db_prueba: Session, catalogo) -> None:
    assert buscador.calcular_embeddings(db_prueba) == 3
    assert db_prueba.scalar(select(func.count()).select_from(EmbeddingTema)) == 3


def test_calcular_embeddings_dos_veces_no_repite_trabajo(db_prueba: Session, catalogo) -> None:
    buscador.calcular_embeddings(db_prueba)

    assert buscador.calcular_embeddings(db_prueba) == 0


def test_si_cambia_el_tema_se_recalcula_su_vector(db_prueba: Session, catalogo) -> None:
    buscador.calcular_embeddings(db_prueba)
    catalogo["algebra"].descripcion = "Ecuaciones, factorizacion y polinomios"

    assert buscador.calcular_embeddings(db_prueba) == 1


def test_el_semantico_devuelve_el_tema_mas_parecido_primero(db_prueba: Session, catalogo) -> None:
    buscador.calcular_embeddings(db_prueba)

    temas_encontrados = buscador.temas_semanticos(db_prueba, "instalaciones electricas de mi casa")

    assert temas_encontrados[0][0] == catalogo["enchufes"].id
    assert 0 < temas_encontrados[0][1] <= 1


# ---------------------------------------------------------------------------
# Resultados: habilidades
# ---------------------------------------------------------------------------


def test_devuelve_las_habilidades_publicadas_del_tema(
    db_prueba: Session, redis_falso, catalogo, aprendiz
) -> None:
    tutor = _tutor(db_prueba, catalogo["algebra"])

    modo, resultados = buscador.buscar(db_prueba, redis_falso, aprendiz.id, "algebra", Modo.LEXICO)

    assert modo == Modo.LEXICO
    [resultado] = resultados
    assert resultado["tutor_id"] == tutor.id
    assert resultado["precio_por_bloque"] == 3
    assert resultado["ruta"] == "Ciencias exactas > Matemáticas"


def test_no_muestra_habilidades_pausadas_ni_cuentas_suspendidas(
    db_prueba: Session, redis_falso, catalogo, aprendiz
) -> None:
    pausado = _tutor(db_prueba, catalogo["algebra"], nombre="Pausado")
    habilidad = habilidades.listar(db_prueba, pausado.id)[0][0]
    habilidades.actualizar(db_prueba, pausado.id, habilidad.id, estado=EstadoHabilidad.PAUSADA)
    suspendido = _tutor(db_prueba, catalogo["algebra"], nombre="Suspendido")
    suspendido.estado_cuenta = EstadoCuenta.SUSPENDIDA
    db_prueba.flush()

    _, resultados = buscador.buscar(db_prueba, redis_falso, aprendiz.id, "algebra", Modo.LEXICO)

    assert resultados == []


def test_no_se_encuentra_a_si_mismo(db_prueba: Session, redis_falso, catalogo) -> None:
    tutor = _tutor(db_prueba, catalogo["algebra"])

    _, resultados = buscador.buscar(db_prueba, redis_falso, tutor.id, "algebra", Modo.LEXICO)

    assert resultados == []


def test_el_filtro_en_linea_deja_solo_a_los_conectados(
    db_prueba: Session, redis_falso, catalogo, aprendiz
) -> None:
    conectado = _tutor(db_prueba, catalogo["algebra"], nombre="Conectado")
    _tutor(db_prueba, catalogo["algebra"], nombre="Desconectado")
    presencia.marcar_en_linea(redis_falso, conectado.id)

    _, resultados = buscador.buscar(db_prueba, redis_falso, aprendiz.id, "algebra", Modo.LEXICO, solo_en_linea=True)

    assert [fila["tutor_id"] for fila in resultados] == [conectado.id]
    assert resultados[0]["en_linea"] is True


def test_la_reputacion_se_oculta_hasta_tener_cinco_valoraciones(
    db_prueba: Session, redis_falso, catalogo, aprendiz
) -> None:
    nuevo = _tutor(db_prueba, catalogo["algebra"], nombre="Nuevo")
    experto = _tutor(db_prueba, catalogo["algebra"], nombre="Experto")
    db_prueba.add(PerfilPublico(usuario_id=nuevo.id, reputacion_promedio=Decimal("5.00"), total_evaluaciones=2))
    db_prueba.add(PerfilPublico(usuario_id=experto.id, reputacion_promedio=Decimal("4.50"), total_evaluaciones=8))
    db_prueba.flush()

    _, resultados = buscador.buscar(db_prueba, redis_falso, aprendiz.id, "algebra", Modo.LEXICO)

    por_tutor = {fila["tutor_nombre"]: fila for fila in resultados}
    assert por_tutor["Nuevo"]["reputacion_promedio"] is None
    assert por_tutor["Experto"]["reputacion_promedio"] == 4.5
    # Con igual pertinencia, primero la mejor reputacion visible.
    assert resultados[0]["tutor_nombre"] == "Experto"


def test_sin_vectores_el_semantico_usa_el_lexico(db_prueba: Session, redis_falso, catalogo, aprendiz) -> None:
    _tutor(db_prueba, catalogo["algebra"])

    modo, resultados = buscador.buscar(db_prueba, redis_falso, aprendiz.id, "algebra", Modo.SEMANTICO)

    assert modo == Modo.LEXICO
    assert len(resultados) == 1


def test_con_vectores_responde_el_semantico(db_prueba: Session, redis_falso, catalogo, aprendiz) -> None:
    tutor = _tutor(db_prueba, catalogo["enchufes"])
    buscador.calcular_embeddings(db_prueba)

    modo, resultados = buscador.buscar(
        db_prueba, redis_falso, aprendiz.id, "instalaciones electricas", Modo.SEMANTICO
    )

    assert modo == Modo.SEMANTICO
    assert resultados[0]["tutor_id"] == tutor.id


# ---------------------------------------------------------------------------
# Ruta HTTP
# ---------------------------------------------------------------------------


def test_la_ruta_responde_con_el_modo_usado(db_prueba: Session, cliente_db: TestClient, catalogo, aprendiz) -> None:
    _tutor(db_prueba, catalogo["algebra"])

    respuesta = cliente_db.get(
        "/buscar", params={"q": "algebra", "modo": "lexico"}, headers=cabecera(aprendiz)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["modo"] == "lexico"
    assert respuesta.json()["resultados"][0]["tema_nombre"] == "Álgebra"


def test_la_ruta_exige_sesion_y_una_duda_de_tres_letras(
    db_prueba: Session, cliente_db: TestClient, aprendiz
) -> None:
    assert cliente_db.get("/buscar", params={"q": "algebra"}).status_code == 401
    assert cliente_db.get("/buscar", params={"q": "ab"}, headers=cabecera(aprendiz)).status_code == 422