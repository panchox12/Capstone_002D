"""Pruebas de habilidades con precio."""
 
import uuid
from decimal import Decimal
 
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
 
from app.core.seguridad import crear_token
from app.modelos.habilidad import EstadoHabilidad
from app.modelos.parametro import ParametroSistema
from app.modelos.usuario import EstadoCuenta, Usuario
from app.modelos.verificacion import ResultadoVerificacion, VerificacionIdentidad
from app.servicios import habilidades as servicio
from app.servicios import temas
 
 
@pytest.fixture()
def precio_maximo(db_prueba: Session) -> ParametroSistema:
    """Parte en 0, que significa sin limite. Cada prueba puede cambiarlo."""
    parametro = ParametroSistema(nombre=servicio.PARAM_PRECIO_MAXIMO, valor="0")
    db_prueba.add(parametro)
    db_prueba.flush()
    return parametro
 
 
@pytest.fixture()
def catalogo(db_prueba: Session) -> dict:
    raiz = temas.crear(db_prueba, "Ciencias exactas")
    grupo = temas.crear(db_prueba, "Matematicas", raiz.id)
    hoja = temas.crear(db_prueba, "Algebra", grupo.id)
    return {"raiz": raiz, "grupo": grupo, "hoja": hoja}
 
 
def _usuario(db: Session, verificado: bool = False) -> Usuario:
    usuario = Usuario(
        correo=f"{uuid.uuid4()}@prueba.cl",
        contrasena_hash="no-aplica",
        nombre_visible="Usuario Prueba",
        estado_cuenta=EstadoCuenta.ACTIVA,
        consentimiento_grabacion=True,
    )
    db.add(usuario)
    db.flush()
    if verificado:
        db.add(VerificacionIdentidad(
            usuario_id=usuario.id,
            resultado=ResultadoVerificacion.APROBADO,
            nivel_confianza=Decimal("92.50"),
            hash_documento=uuid.uuid4().hex + uuid.uuid4().hex,
        ))
        db.flush()
    return usuario
 
 
def _cabecera(usuario: Usuario) -> dict:
    return {"Authorization": f"Bearer {crear_token(sujeto=str(usuario.id))}"}
 
 
# --- Servicio -------------------------------------------------------------------
 
 
def test_se_publica_en_un_tema_del_ultimo_nivel(db_prueba: Session, precio_maximo, catalogo) -> None:
    usuario = _usuario(db_prueba)
 
    habilidad = servicio.publicar(db_prueba, usuario.id, catalogo["hoja"].id, 3)
 
    assert habilidad.precio_por_bloque == 3
    assert habilidad.estado == EstadoHabilidad.PUBLICADA
 
 
def test_no_se_publica_en_un_tema_general(db_prueba: Session, precio_maximo, catalogo) -> None:
    usuario = _usuario(db_prueba)
 
    for tema in (catalogo["raiz"], catalogo["grupo"]):
        with pytest.raises(servicio.TemaNoOfrecible):
            servicio.publicar(db_prueba, usuario.id, tema.id, 3)
 
 
def test_el_precio_tiene_que_ser_mayor_que_cero(db_prueba: Session, precio_maximo, catalogo) -> None:
    usuario = _usuario(db_prueba)
 
    with pytest.raises(servicio.PrecioInvalido):
        servicio.publicar(db_prueba, usuario.id, catalogo["hoja"].id, 0)
 
 
def test_el_precio_maximo_se_respeta_solo_si_esta_activo(db_prueba: Session, precio_maximo, catalogo) -> None:
    usuario = _usuario(db_prueba)
    servicio.publicar(db_prueba, usuario.id, catalogo["hoja"].id, 500)
 
    precio_maximo.valor = "10"
    db_prueba.flush()
    otro = _usuario(db_prueba)
    with pytest.raises(servicio.PrecioInvalido):
        servicio.publicar(db_prueba, otro.id, catalogo["hoja"].id, 11)
    servicio.publicar(db_prueba, otro.id, catalogo["hoja"].id, 10)
 
 
def test_no_se_publica_dos_veces_el_mismo_tema(db_prueba: Session, precio_maximo, catalogo) -> None:
    usuario = _usuario(db_prueba)
    servicio.publicar(db_prueba, usuario.id, catalogo["hoja"].id, 3)
 
    with pytest.raises(servicio.HabilidadDuplicada):
        servicio.publicar(db_prueba, usuario.id, catalogo["hoja"].id, 5)
 
 
def test_nadie_edita_la_habilidad_de_otro(db_prueba: Session, precio_maximo, catalogo) -> None:
    duena = _usuario(db_prueba)
    intruso = _usuario(db_prueba)
    habilidad = servicio.publicar(db_prueba, duena.id, catalogo["hoja"].id, 3)
 
    with pytest.raises(servicio.HabilidadNoEncontrada):
        servicio.actualizar(db_prueba, intruso.id, habilidad.id, precio=1)
 
 
# --- Endpoints ------------------------------------------------------------------
 
 
def test_sin_identidad_verificada_no_se_puede_ofrecer(
    cliente_db: TestClient, db_prueba: Session, precio_maximo, catalogo
) -> None:
    usuario = _usuario(db_prueba, verificado=False)
 
    respuesta = cliente_db.post(
        "/habilidades",
        json={"tema_id": catalogo["hoja"].id, "precio_por_bloque": 3},
        headers=_cabecera(usuario),
    )
 
    assert respuesta.status_code == 403
 
 
def test_con_identidad_verificada_se_publica_y_aparece_en_mis_habilidades(
    cliente_db: TestClient, db_prueba: Session, precio_maximo, catalogo
) -> None:
    usuario = _usuario(db_prueba, verificado=True)
 
    respuesta = cliente_db.post(
        "/habilidades",
        json={"tema_id": catalogo["hoja"].id, "precio_por_bloque": 3},
        headers=_cabecera(usuario),
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["tema_nombre"] == "Algebra"
 
    mias = cliente_db.get("/habilidades/mias", headers=_cabecera(usuario))
    assert [h["precio_por_bloque"] for h in mias.json()] == [3]
 
 
def test_pausar_una_habilidad(
    cliente_db: TestClient, db_prueba: Session, precio_maximo, catalogo
) -> None:
    usuario = _usuario(db_prueba, verificado=True)
    habilidad = servicio.publicar(db_prueba, usuario.id, catalogo["hoja"].id, 3)
 
    respuesta = cliente_db.patch(
        f"/habilidades/{habilidad.id}",
        json={"estado": "pausada"},
        headers=_cabecera(usuario),
    )
 
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "pausada"