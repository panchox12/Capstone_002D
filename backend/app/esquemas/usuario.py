"""Esquemas de entrada y salida para usuarios."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modelos.usuario import EstadoCuenta


class UsuarioCrear(BaseModel):
    """Lo que el usuario envia al registrarse."""

    correo: EmailStr
    contrasena: str = Field(min_length=10, max_length=72)
    nombre_visible: str = Field(min_length=2, max_length=80)
    acepta_terminos: bool
    consentimiento_grabacion: bool

    @field_validator("contrasena")
    @classmethod
    def validar_fortaleza(cls, valor: str) -> str:
        if not any(caracter.isdigit() for caracter in valor):
            raise ValueError("La contrasena debe incluir al menos un numero")
        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError("La contrasena debe incluir al menos una letra")
        return valor

    @field_validator("acepta_terminos")
    @classmethod
    def exigir_terminos(cls, valor: bool) -> bool:
        if not valor:
            raise ValueError("Debe aceptar los terminos y condiciones")
        return valor

    @field_validator("consentimiento_grabacion")
    @classmethod
    def exigir_consentimiento(cls, valor: bool) -> bool:
        if not valor:
            raise ValueError(
                "Debe autorizar la grabacion de las sesiones para usar la plataforma"
            )
        return valor


class UsuarioLeer(BaseModel):
    """Lo que la API devuelve. Nunca incluye contrasena ni hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    correo: EmailStr
    nombre_visible: str
    estado_cuenta: EstadoCuenta
    consentimiento_grabacion: bool
    creado_en: datetime


class TokenRespuesta(BaseModel):
    """Respuesta del login, con el formato que espera el estandar OAuth2."""

    access_token: str
    token_type: str = "bearer"