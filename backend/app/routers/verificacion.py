"""Endpoint de verificacion de identidad.
 
Recibe las imagenes codificadas en base64 dentro de un JSON, y no como
archivos subidos. Al subir archivos, el framework escribe en un archivo
temporal en disco todo lo que supere cierto tamano (por defecto, alrededor
de 1 MB), antes de que nuestro codigo se ejecute. Con JSON, el cuerpo
completo de la peticion se lee en memoria.
"""
 
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Base64Bytes, BaseModel, field_validator
from sqlalchemy.orm import Session
 
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.modelos.usuario import Usuario
from app.servicios import verificacion as servicio
 
router = APIRouter(prefix="/verificacion", tags=["Verificacion de identidad"])
 
TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024
 
# Los primeros bytes de un archivo identifican su formato real,
# sin confiar en lo que declare el cliente.
FIRMAS_PERMITIDAS = (
    b"\xff\xd8\xff",          # JPEG
    b"\x89PNG\r\n\x1a\n",     # PNG
)
 
 
class SolicitudVerificacion(BaseModel):
    """Las tres imagenes en base64, sin el prefijo data:image/...;base64,
    mas el consentimiento explicito para tratar datos biometricos."""
 
    documento_frontal: Base64Bytes
    documento_reverso: Base64Bytes
    rostro: Base64Bytes
    consentimiento_biometrico: bool
 
    @field_validator("consentimiento_biometrico")
    @classmethod
    def exigir_consentimiento(cls, valor: bool) -> bool:
        if not valor:
            raise ValueError(
                "Debes autorizar el tratamiento de tus datos biometricos para verificar tu identidad"
            )
        return valor
 
 
def _validar_imagen(datos: bytes, campo: str) -> None:
    if not datos.startswith(FIRMAS_PERMITIDAS):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"{campo} debe ser una imagen JPEG o PNG",
        )
    if len(datos) > TAMANO_MAXIMO_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"{campo} supera los 5 MB permitidos",
        )
 
 
@router.post("", status_code=status.HTTP_201_CREATED, summary="Verificar identidad")
def verificar_identidad(
    datos: SolicitudVerificacion,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> dict:
    _validar_imagen(datos.documento_frontal, "documento_frontal")
    _validar_imagen(datos.documento_reverso, "documento_reverso")
    _validar_imagen(datos.rostro, "rostro")
 
    try:
        registro = servicio.verificar(db, usuario.id, datos.documento_frontal, datos.rostro)
    except servicio.YaVerificado:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Tu identidad ya esta verificada"
        ) from None
    except servicio.DocumentoYaAsociado:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ese documento ya esta asociado a otra cuenta"
        ) from None
    except servicio.DocumentoIlegible:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No pudimos leer el RUN del documento. Toma la foto con buena luz y sin reflejos",
        ) from None
    except servicio.ProveedorNoDisponible:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "La verificacion no esta disponible en este momento. Intenta mas tarde",
        ) from None
 
    # No se devuelve el hash: el usuario no lo necesita.
    return {
        "resultado": registro.resultado.value,
        "nivel_confianza": float(registro.nivel_confianza),
        "fecha": registro.creado_en.isoformat(),
    }