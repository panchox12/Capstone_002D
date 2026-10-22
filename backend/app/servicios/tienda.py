"""Tienda: paquetes de tokens y compras.

El pago todavia es simulado: toda compra se aprueba al instante. Cuando se
conecte un medio de pago real, la creacion del lote se movera al momento
en que el medio confirme el pago, y la compra esperara en estado pendiente.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.compra import Compra, EstadoCompra
from app.modelos.lote_tokens import LoteDeTokens, OrigenLote, TipoSaldo
from app.servicios import tokens

MEDIO_SIMULADO = "simulado"


@dataclass(frozen=True)
class Paquete:
    codigo: str
    cantidad_tokens: int
    monto_pesos: int

    @property
    def pesos_por_token(self) -> int:
        return round(self.monto_pesos / self.cantidad_tokens)


PAQUETES = {
    paquete.codigo: paquete
    for paquete in (
        Paquete("basico", 5, 490),
        Paquete("popular", 13, 990),
        Paquete("volumen", 30, 1990),
    )
}


class PaqueteInexistente(Exception):
    """El codigo de paquete no esta en la tienda."""


def comprar(db: Session, usuario_id: uuid.UUID, codigo: str) -> Compra:
    paquete = PAQUETES.get(codigo)
    if paquete is None:
        raise PaqueteInexistente()

    compra = Compra(
        usuario_id=usuario_id,
        paquete=paquete.codigo,
        cantidad_tokens=paquete.cantidad_tokens,
        monto_pesos=paquete.monto_pesos,
        medio_pago=MEDIO_SIMULADO,
        estado=EstadoCompra.PENDIENTE,
        fecha=tokens.ahora(),
    )
    db.add(compra)
    db.flush()

    # Pago simulado: se aprueba de inmediato y los tokens entran como un lote nuevo.
    lote = tokens.otorgar(
        db,
        usuario_id=usuario_id,
        cantidad=paquete.cantidad_tokens,
        tipo_saldo=TipoSaldo.PAGADO,
        origen=OrigenLote.COMPRA,
        dias_vigencia=tokens.dias_de_vigencia(db, OrigenLote.COMPRA),
    )
    compra.estado = EstadoCompra.PAGADA
    compra.lote_id = lote.id
    db.flush()
    return compra


def historial(db: Session, usuario_id: uuid.UUID) -> list[tuple[Compra, LoteDeTokens | None]]:
    #Las compras del usuario, la mas reciente primero, cada una con su lote.
    sentencia = (
        select(Compra, LoteDeTokens)
        .outerjoin(LoteDeTokens, LoteDeTokens.id == Compra.lote_id)
        .where(Compra.usuario_id == usuario_id)
        .order_by(Compra.fecha.desc())
    )
    return [(fila[0], fila[1]) for fila in db.execute(sentencia).all()]
