"""Indicadores de la economia de tokens para el panel del administrador.
 
Todos se calculan al momento desde las tablas de lotes, transacciones,
retenciones y compras: no hay nada guardado aparte que se pueda desfasar.
La ventana de tiempo es de 30 dias hacia atras.
"""
 
from datetime import timedelta
 
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session
 
from app.modelos.compra import Compra, EstadoCompra
from app.modelos.lote_tokens import EstadoLote, LoteDeTokens, TipoSaldo
from app.modelos.parametro import ParametroSistema
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.sesion import EstadoSesion, Sesion
from app.modelos.transaccion import TipoTransaccion, Transaccion
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import tokens
 
DIAS_VENTANA = 30
 
 
class ParametroNoEncontrado(Exception):
    pass
 
 
def _suma(db: Session, columna, *condiciones) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(columna), 0)).where(*condiciones)))
 
 
def _proporcion(parte: int, total: int) -> float:
    # Sin datos todavia, el indicador es cero en vez de una division por cero.
    return round(parte / total, 4) if total else 0.0
 
 
def calcular(db: Session) -> dict:
    ahora = tokens.ahora()
    desde = ahora - timedelta(days=DIAS_VENTANA)
 
    masa = _suma(
        db,
        LoteDeTokens.cantidad_restante,
        LoteDeTokens.estado == EstadoLote.VIGENTE,
        LoteDeTokens.fecha_vencimiento > ahora,
    )
    retenido = _suma(db, Retencion.cantidad, Retencion.estado == EstadoRetencion.ACTIVA)
    entregados = _suma(db, LoteDeTokens.cantidad_original, LoteDeTokens.fecha_recepcion >= desde)
    # Lo que quedaba en los lotes cuando vencieron: tokens que nadie alcanzo a usar.
    vencidos = _suma(
        db,
        LoteDeTokens.cantidad_restante,
        LoteDeTokens.fecha_vencimiento >= desde,
        LoteDeTokens.fecha_vencimiento <= ahora,
    )
    consumidos = _suma(
        db, Transaccion.cantidad, Transaccion.tipo == TipoTransaccion.CONSUMO, Transaccion.fecha >= desde
    )
    consumidos_gratis = int(
        db.scalar(
            select(func.coalesce(func.sum(Transaccion.cantidad), 0))
            .join(LoteDeTokens, LoteDeTokens.id == Transaccion.lote_id)
            .where(
                Transaccion.tipo == TipoTransaccion.CONSUMO,
                Transaccion.fecha >= desde,
                LoteDeTokens.tipo_saldo == TipoSaldo.GRATIS,
            )
        )
    )
    activos = db.scalar(select(func.count()).where(Usuario.estado_cuenta == EstadoCuenta.ACTIVA))
    compradores = db.scalar(select(func.count(distinct(Compra.usuario_id))).where(Compra.estado == EstadoCompra.PAGADA))
    sesiones = db.scalar(
        select(func.count()).where(Sesion.estado == EstadoSesion.TERMINADA, Sesion.fecha_cierre >= desde)
    )
 
    return {
        "dias_ventana": DIAS_VENTANA,
        "masa_circulante": masa,
        "tokens_retenidos": retenido,
        "tokens_entregados": entregados,
        "tokens_consumidos": consumidos,
        "tokens_vencidos": vencidos,
        # Cuantas veces se movio la masa en la ventana.
        "velocidad": _proporcion(consumidos, masa),
        "tasa_caducidad": _proporcion(vencidos, entregados),
        # Parte de lo consumido que se pago con tokens gratis.
        "cobertura_gratuita": _proporcion(consumidos_gratis, consumidos),
        "conversion": _proporcion(compradores, activos),
        "usuarios_activos": activos,
        "sesiones_terminadas": sesiones,
    }
 
 
def listar_parametros(db: Session) -> list[ParametroSistema]:
    return list(db.execute(select(ParametroSistema).order_by(ParametroSistema.nombre)).scalars())
 
 
def cambiar_parametro(db: Session, nombre: str, valor: int) -> ParametroSistema:
    # Todos los parametros de Cachai son enteros no negativos.
    parametro = db.get(ParametroSistema, nombre, with_for_update=True)
    if parametro is None:
        raise ParametroNoEncontrado()
    parametro.valor = str(valor)
    db.flush()
    return parametro