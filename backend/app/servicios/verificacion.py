"""Verificacion de identidad sin guardar imagenes.
 
Las imagenes llegan como bytes en memoria, se usan dentro de verificar()
y no existe ninguna instruccion que las escriba: ni a disco, ni a la base
de datos, ni a un bucket, ni a los registros. Solo persisten el resultado,
el nivel de confianza y el hash con sal del documento.
"""
 
import hashlib
import uuid
from decimal import Decimal
 
from sqlalchemy import select
from sqlalchemy.orm import Session
 
from app.core.config import configuracion
from app.modelos.verificacion import ResultadoVerificacion, VerificacionIdentidad
 
UMBRAL_APROBACION = Decimal("85.00")
 
 
class YaVerificado(Exception):
    """El usuario ya tiene una verificacion aprobada."""
 
 
class DocumentoYaAsociado(Exception):
    """El documento ya esta verificado en otra cuenta."""
 
 
class DocumentoIlegible(Exception):
    """No se pudo leer un RUN valido en la imagen del documento."""
 
 
class ProveedorNoDisponible(Exception):
    """El servicio externo de verificacion no respondio."""
 
 
def hashear_documento(numero_documento: str) -> str:
    """Hash con sal del numero de documento, normalizado."""
    normalizado = numero_documento.replace(".", "").replace("-", "").upper().strip()
    material = f"{configuracion.sal_documento}:{normalizado}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()
 
 
# ---------------------------------------------------------------------------
# Proveedores
# PROVEEDOR_IDENTIDAD=simulado  -> desarrollo y pruebas, sin costo ni AWS
# PROVEEDOR_IDENTIDAD=aws       -> Amazon Rekognition (app/servicios/rekognition.py)
# ---------------------------------------------------------------------------
 
 
def _comparar_rostros_simulado(imagen_documento: bytes, imagen_rostro: bytes) -> Decimal:
    if not imagen_documento or not imagen_rostro:
        return Decimal("0")
    return Decimal("92.50")
 
 
def _extraer_numero_simulado(imagen_documento: bytes) -> str:
    """La misma imagen da siempre el mismo numero, e imagenes distintas dan
    numeros distintos. Asi se pueden probar varias cuentas."""
    return "SIM" + hashlib.sha256(imagen_documento).hexdigest()[:12]
 
 
def comparar_rostros(imagen_documento: bytes, imagen_rostro: bytes) -> Decimal:
    """Nivel de confianza de la comparacion, de 0 a 100."""
    if configuracion.proveedor_identidad == "aws":
        from app.servicios import rekognition  # solo se carga si se usa AWS
 
        return rekognition.comparar_rostros(imagen_documento, imagen_rostro)
    return _comparar_rostros_simulado(imagen_documento, imagen_rostro)
 
 
def extraer_numero_documento(imagen_documento: bytes) -> str | None:
    """RUN leido del documento, o None si no se pudo leer."""
    if configuracion.proveedor_identidad == "aws":
        from app.servicios import rekognition
 
        return rekognition.extraer_numero_documento(imagen_documento)
    return _extraer_numero_simulado(imagen_documento)
 
 
# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------
 
 
def esta_verificado(db: Session, usuario_id: uuid.UUID) -> bool:
    sentencia = select(VerificacionIdentidad.id).where(
        VerificacionIdentidad.usuario_id == usuario_id,
        VerificacionIdentidad.resultado == ResultadoVerificacion.APROBADO,
    )
    return db.execute(sentencia).first() is not None
 
 
def _documento_ya_aprobado(db: Session, hash_documento: str) -> bool:
    sentencia = select(VerificacionIdentidad.id).where(
        VerificacionIdentidad.hash_documento == hash_documento,
        VerificacionIdentidad.resultado == ResultadoVerificacion.APROBADO,
    )
    return db.execute(sentencia).first() is not None
 
 
def verificar(
    db: Session,
    usuario_id: uuid.UUID,
    imagen_documento: bytes,
    imagen_rostro: bytes,
) -> VerificacionIdentidad:
    """Procesa las imagenes en memoria y guarda solo el resultado."""
    if esta_verificado(db, usuario_id):
        raise YaVerificado()
 
    # --- Aca, y solo aca, se usan las imagenes ---
    numero = extraer_numero_documento(imagen_documento)
    if numero is None:
        raise DocumentoIlegible()
    confianza = comparar_rostros(imagen_documento, imagen_rostro)
    hash_doc = hashear_documento(numero)
    # --- Desde aca en adelante ya no se usan ---
 
    aprobado = confianza >= UMBRAL_APROBACION
 
    # Este usuario no esta verificado, asi que si el documento ya aparece
    # aprobado, es porque pertenece a otra cuenta.
    if aprobado and _documento_ya_aprobado(db, hash_doc):
        raise DocumentoYaAsociado()
 
    registro = VerificacionIdentidad(
        usuario_id=usuario_id,
        resultado=ResultadoVerificacion.APROBADO if aprobado else ResultadoVerificacion.RECHAZADO,
        nivel_confianza=confianza,
        hash_documento=hash_doc,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro