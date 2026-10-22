"""Saldo propio y videos publicitarios."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.tokens import LoteLeer, SaldoLeer, VideoLeer
from app.modelos.lote_tokens import TipoSaldo
from app.modelos.usuario import Usuario
from app.servicios import entradas, parametros, tokens

router = APIRouter(prefix="/tokens", tags=["Tokens"])


@router.get("/saldo", response_model=SaldoLeer, summary="Mi saldo, por tipo y por lote")
def mi_saldo(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> SaldoLeer:
    gratis = tokens.calcular_saldo(db, usuario.id, TipoSaldo.GRATIS)
    pagado = tokens.calcular_saldo(db, usuario.id, TipoSaldo.PAGADO)
    return SaldoLeer(
        gratis=gratis,
        pagado=pagado,
        total=gratis + pagado,
        retenidos=tokens.calcular_retenido(db, usuario.id),
        tope_saldo_gratis=parametros.obtener_entero(db, entradas.PARAM_TOPE_GRATIS),
        videos_vistos_hoy=entradas.videos_vistos_hoy(db, usuario.id),
        tope_videos_por_dia=parametros.obtener_entero(db, entradas.PARAM_TOPE_VIDEOS),
        lotes=[LoteLeer.model_validate(lote) for lote in tokens.lotes_vigentes(db, usuario.id)],
    )


@router.post(
    "/videos",
    response_model=VideoLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un video visto",
)
def ver_video(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> VideoLeer:
    try:
        video = entradas.ver_video(db, usuario.id)
    except entradas.TopeDeVideos:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Ya viste todos los videos de hoy. Vuelve a intentarlo mas tarde",
        ) from None
    except entradas.SaldoGratisCompleto:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Tu saldo gratuito ya esta completo",
        ) from None

    db.commit()
    return VideoLeer(
        tokens_otorgados=video.tokens_otorgados,
        videos_vistos_hoy=entradas.videos_vistos_hoy(db, usuario.id),
        tope_videos_por_dia=parametros.obtener_entero(db, entradas.PARAM_TOPE_VIDEOS),
    )
