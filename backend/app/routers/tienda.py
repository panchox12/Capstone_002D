"""Paquetes de tokens, compras e historial de compras."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.tienda import CompraCrear, CompraLeer, PaqueteLeer
from app.modelos.compra import Compra
from app.modelos.lote_tokens import LoteDeTokens
from app.modelos.usuario import Usuario
from app.servicios import tienda as servicio
from app.servicios import tokens

router = APIRouter(prefix="/tienda", tags=["Tienda"])


def _leer(compra: Compra, lote: LoteDeTokens | None) -> CompraLeer:
    vencida = lote is not None and lote.fecha_vencimiento <= tokens.ahora()
    return CompraLeer(
        id=compra.id,
        paquete=compra.paquete,
        cantidad_tokens=compra.cantidad_tokens,
        monto_pesos=compra.monto_pesos,
        estado=compra.estado,
        fecha=compra.fecha,
        fecha_vencimiento=lote.fecha_vencimiento if lote else None,
        tokens_restantes=lote.cantidad_restante if lote else 0,
        vencida=vencida,
    )


@router.get("/paquetes", response_model=list[PaqueteLeer], summary="Paquetes a la venta")
def paquetes() -> list[PaqueteLeer]:
    return [
        PaqueteLeer(
            codigo=paquete.codigo,
            cantidad_tokens=paquete.cantidad_tokens,
            monto_pesos=paquete.monto_pesos,
            pesos_por_token=paquete.pesos_por_token,
        )
        for paquete in servicio.PAQUETES.values()
    ]


@router.post(
    "/compras",
    response_model=CompraLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Comprar un paquete",
)
def comprar(
    datos: CompraCrear,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> CompraLeer:
    try:
        compra = servicio.comprar(db, usuario.id, datos.paquete)
    except servicio.PaqueteInexistente:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Ese paquete no existe") from None

    db.commit()
    return _leer(compra, db.get(LoteDeTokens, compra.lote_id))


@router.get("/compras", response_model=list[CompraLeer], summary="Mi historial de compras")
def mis_compras(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> list[CompraLeer]:
    return [_leer(compra, lote) for compra, lote in servicio.historial(db, usuario.id)]
