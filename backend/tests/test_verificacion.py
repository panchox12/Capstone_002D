"""Pruebas de verificacion de identidad, con enfasis en no persistencia."""
 
import base64
 
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session
 
from app.core.seguridad import hashear_contrasena
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import verificacion as servicio
 
JPEG_A = b"\xff\xd8\xff\xe0" + b"documento-a"
JPEG_B = b"\xff\xd8\xff\xe0" + b"documento-b"
PDF = b"%PDF-1.4 documento"
 
 
def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")
 
 
def _crear_usuario(db: Session, correo: str) -> Usuario:
    usuario = Usuario(
        correo=correo,
        contrasena_hash=hashear_contrasena("cachai12345"),
        nombre_visible="Usuario Prueba",
        estado_cuenta=EstadoCuenta.ACTIVA,
        consentimiento_grabacion=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
 
 
def _token(cliente: TestClient, correo: str) -> str:
    respuesta = cliente.post("/auth/login", data={"username": correo, "password": "cachai12345"})
    return respuesta.json()["access_token"]
 
 
# --- Cumplimiento: ley 21.719 -------------------------------------------------
 
 
def test_la_tabla_no_guarda_imagenes_ni_documento_en_claro(motor_prueba) -> None:
    columnas = {c["name"] for c in inspect(motor_prueba).get_columns("verificacion_identidad")}
 
    prohibidas = ("foto", "imagen", "selfie", "url", "ruta", "numero")
    for columna in columnas:
        assert not any(fragmento in columna for fragmento in prohibidas), columna
 
 
def test_el_hash_normaliza_el_formato_del_documento() -> None:
    assert servicio.hashear_documento("11.111.111-1") == servicio.hashear_documento("111111111")
    assert len(servicio.hashear_documento("11111111-1")) == 64
 
 
# --- Servicio -----------------------------------------------------------------
 
 
def test_una_verificacion_valida_queda_aprobada(db_prueba: Session) -> None:
    usuario = _crear_usuario(db_prueba, "a@duoc.cl")
 
    registro = servicio.verificar(db_prueba, usuario.id, JPEG_A, JPEG_A)
 
    assert registro.resultado.value == "aprobado"
    assert servicio.esta_verificado(db_prueba, usuario.id)
 
 
def test_no_se_puede_verificar_dos_veces(db_prueba: Session) -> None:
    usuario = _crear_usuario(db_prueba, "a@duoc.cl")
    servicio.verificar(db_prueba, usuario.id, JPEG_A, JPEG_A)
 
    with pytest.raises(servicio.YaVerificado):
        servicio.verificar(db_prueba, usuario.id, JPEG_A, JPEG_A)
 
 
def test_un_documento_no_puede_verificar_dos_cuentas(db_prueba: Session) -> None:
    primera = _crear_usuario(db_prueba, "a@duoc.cl")
    segunda = _crear_usuario(db_prueba, "b@duoc.cl")
    servicio.verificar(db_prueba, primera.id, JPEG_A, JPEG_A)
 
    with pytest.raises(servicio.DocumentoYaAsociado):
        servicio.verificar(db_prueba, segunda.id, JPEG_A, JPEG_A)
 
 
def test_documentos_distintos_verifican_cuentas_distintas(db_prueba: Session) -> None:
    primera = _crear_usuario(db_prueba, "a@duoc.cl")
    segunda = _crear_usuario(db_prueba, "b@duoc.cl")
 
    servicio.verificar(db_prueba, primera.id, JPEG_A, JPEG_A)
    registro = servicio.verificar(db_prueba, segunda.id, JPEG_B, JPEG_B)
 
    assert registro.resultado.value == "aprobado"
 
 
# --- Endpoint -----------------------------------------------------------------
 
 
def test_el_endpoint_rechaza_archivos_que_no_son_imagen(
    cliente_db: TestClient, db_prueba: Session
) -> None:
    _crear_usuario(db_prueba, "c@duoc.cl")
    token = _token(cliente_db, "c@duoc.cl")
 
    respuesta = cliente_db.post(
        "/verificacion",
        json={
            "documento_frontal": _b64(PDF),
            "documento_reverso": _b64(JPEG_A),
            "rostro": _b64(JPEG_A),
            "consentimiento_biometrico": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
 
    assert respuesta.status_code == 415
 
 
def test_el_endpoint_no_devuelve_el_hash_del_documento(
    cliente_db: TestClient, db_prueba: Session
) -> None:
    _crear_usuario(db_prueba, "d@duoc.cl")
    token = _token(cliente_db, "d@duoc.cl")
 
    respuesta = cliente_db.post(
        "/verificacion",
        json={
            "documento_frontal": _b64(JPEG_A),
            "documento_reverso": _b64(JPEG_A),
            "rostro": _b64(JPEG_A),
            "consentimiento_biometrico": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
 
    assert respuesta.status_code == 201
    assert "hash_documento" not in respuesta.json()
 
 
def test_sin_consentimiento_biometrico_no_se_procesa(
    cliente_db: TestClient, db_prueba: Session
) -> None:
    _crear_usuario(db_prueba, "e@duoc.cl")
    token = _token(cliente_db, "e@duoc.cl")
 
    respuesta = cliente_db.post(
        "/verificacion",
        json={
            "documento_frontal": _b64(JPEG_A),
            "documento_reverso": _b64(JPEG_A),
            "rostro": _b64(JPEG_A),
            "consentimiento_biometrico": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
 
    assert respuesta.status_code == 422