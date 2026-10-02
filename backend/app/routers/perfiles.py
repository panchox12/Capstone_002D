"""Endpoints de perfiles publicos y codigo QR."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.habilidad import HabilidadLeer
from app.esquemas.perfil import PerfilActualizar, PerfilPublicoLeer
from app.modelos.usuario import Usuario
from app.servicios import habilidades as servicio_habilidades
from app.servicios import perfiles as servicio

router = APIRouter(prefix="/perfiles", tags=["Perfiles"])


@router.patch("/mio", response_model=PerfilPublicoLeer, summary="Editar perfil propio")
def actualizar_mio(
    datos: PerfilActualizar,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> PerfilPublicoLeer:
    try:
        perfil = servicio.actualizar_propio(
            db,
            usuario.id,
            biografia=datos.biografia,
            enlace_personalizado=datos.enlace_personalizado,
        )
    except servicio.EnlaceInvalido:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El enlace solo admite letras minusculas, numeros, guiones y guiones bajos (3-30 caracteres)",
        ) from None
    except servicio.EnlaceEnUso:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ese enlace ya esta tomado por otro usuario",
        ) from None

    db.commit()
    habilidades = [
        HabilidadLeer(
            id=hab.id,
            tema_id=tema.id,
            tema_nombre=tema.nombre,
            precio_por_bloque=hab.precio_por_bloque,
            estado=hab.estado,
        )
        for hab, tema in servicio_habilidades.listar(db, usuario.id, solo_publicadas=True)
    ]
    identificador = perfil.enlace_personalizado or str(usuario.id)
    return PerfilPublicoLeer(
        usuario_id=usuario.id,
        nombre_visible=usuario.nombre_visible,
        biografia=perfil.biografia,
        enlace_personalizado=perfil.enlace_personalizado,
        url_perfil=servicio.url_perfil(identificador),
        reputacion_promedio=perfil.reputacion_promedio,
        total_evaluaciones=perfil.total_evaluaciones,
        consultas_completadas=perfil.consultas_completadas,
        habilidades=habilidades,
    )


@router.get("/{identificador}", response_model=PerfilPublicoLeer, summary="Ver perfil publico")
def ver_perfil(
    identificador: str,
    db: Session = Depends(obtener_db),
) -> PerfilPublicoLeer:
    try:
        usuario, perfil = servicio.obtener_publico(db, identificador)
    except servicio.PerfilNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil no encontrado") from None

    habilidades = [
        HabilidadLeer(
            id=hab.id,
            tema_id=tema.id,
            tema_nombre=tema.nombre,
            precio_por_bloque=hab.precio_por_bloque,
            estado=hab.estado,
        )
        for hab, tema in servicio_habilidades.listar(db, usuario.id, solo_publicadas=True)
    ]
    slug = perfil.enlace_personalizado or str(usuario.id)
    return PerfilPublicoLeer(
        usuario_id=usuario.id,
        nombre_visible=usuario.nombre_visible,
        biografia=perfil.biografia,
        enlace_personalizado=perfil.enlace_personalizado,
        url_perfil=servicio.url_perfil(slug),
        reputacion_promedio=perfil.reputacion_promedio,
        total_evaluaciones=perfil.total_evaluaciones,
        consultas_completadas=perfil.consultas_completadas,
        habilidades=habilidades,
    )


@router.get("/{identificador}/qr", summary="Descargar QR del perfil")
def obtener_qr(
    identificador: str,
    db: Session = Depends(obtener_db),
) -> Response:
    try:
        usuario, perfil = servicio.obtener_publico(db, identificador)
    except servicio.PerfilNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil no encontrado") from None

    slug = perfil.enlace_personalizado or str(usuario.id)
    url = servicio.url_perfil(slug)
    imagen_png = servicio.generar_qr_png(url)
    return Response(content=imagen_png, media_type="image/png")