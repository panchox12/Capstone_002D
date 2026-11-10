"""Esquemas del saldo y de los videos."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.transaccion import TipoTransaccion


class LoteLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_saldo: TipoSaldo
    origen: OrigenLote
    cantidad_restante: int
    fecha_vencimiento: datetime


class SaldoLeer(BaseModel):
    """Todo lo que la pantalla de inicio necesita para mostrar el saldo."""

    gratis: int
    pagado: int
    total: int
    retenidos: int
    tope_saldo_gratis: int
    videos_vistos_hoy: int
    tope_videos_por_dia: int
    lotes: list[LoteLeer]


# Una linea del historial: cuanto entro o salio, por que y con quien.
class MovimientoLeer(BaseModel):
    id: uuid.UUID
    fecha: datetime
    tipo: TipoTransaccion
    origen: OrigenLote
    # Negativa cuando los tokens salen del saldo.
    cantidad: int
    saldo_resultante: int
    tema: str | None = None
    contraparte: str | None = None


class VideoLeer(BaseModel):
    tokens_otorgados: int
    videos_vistos_hoy: int
    tope_videos_por_dia: int