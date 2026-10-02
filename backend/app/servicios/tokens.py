"""Motor de tokens: saldo, entradas, retenciones, liberaciones y reembolsos.
 
Reglas que este modulo garantiza:
- El saldo nunca se guarda: se calcula sumando lo que queda en lotes vigentes.
- Se consume primero el lote que vence antes; en empate, el gratuito.
- Todo movimiento queda registrado en Transaccion, que es de solo agregado.
- Ninguna funcion hace commit: quien la llama confirma todo junto, o nada.
"""
 
import uuid
from datetime import datetime, timedelta, timezone
 
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
 
from app.modelos.lote_tokens import EstadoLote, LoteDeTokens, OrigenLote, TipoSaldo
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.transaccion import TipoTransaccion, Transaccion
from app.servicios import parametros
 
# ---------------------------------------------------------------------------
# Nombres de parametros, en un solo lugar para no escribirlos a mano dos veces
# ---------------------------------------------------------------------------
 
PARAM_DIAS_GRATIS = "dias_vencimiento_gratis"
PARAM_DIAS_COMPRADO = "dias_vencimiento_comprado"
PARAM_DIAS_ENSENADO = "dias_vencimiento_enseñado"
 
_PARAM_DIAS_POR_ORIGEN = {
    OrigenLote.ENTREGA_SEMANAL: PARAM_DIAS_GRATIS,
    OrigenLote.VIDEO: PARAM_DIAS_GRATIS,
    OrigenLote.COMPRA: PARAM_DIAS_COMPRADO,
    OrigenLote.PAGO_POR_ENSENAR: PARAM_DIAS_ENSENADO,
    OrigenLote.COMPENSACION: PARAM_DIAS_COMPRADO,
}
 
_TIPO_TRANSACCION_POR_ORIGEN = {
    OrigenLote.COMPRA: TipoTransaccion.COMPRA,
    OrigenLote.COMPENSACION: TipoTransaccion.COMPENSACION,
}

# ---------------------------------------------------------------------------
# Errores propios del motor
# ---------------------------------------------------------------------------
 
 
class SaldoInsuficiente(Exception):
    #El usuario no tiene tokens vigentes suficientes.
 
    def __init__(self, disponible: int, requerido: int):
        super().__init__(f"Saldo insuficiente: disponible {disponible}, requerido {requerido}")
        self.disponible = disponible
        self.requerido = requerido
 
 
class RetencionNoActiva(Exception):
    """La retencion no existe, o ya fue liberada o reembolsada."""

# ---------------------------------------------------------------------------
# Reloj y vigencias
# ---------------------------------------------------------------------------
 
 
def ahora() -> datetime:
    #Unico reloj del motor: el del servidor, en UTC. Nunca el del navegador.
    return datetime.now(timezone.utc)
 
 
def dias_de_vigencia(db: Session, origen: OrigenLote) -> int:
    #Cuantos dias dura un lote segun de donde vinieron sus tokens.
    return parametros.obtener_entero(db, _PARAM_DIAS_POR_ORIGEN[origen])

# ---------------------------------------------------------------------------
# Saldo
# ---------------------------------------------------------------------------
 
 
def calcular_saldo(
    db: Session,
    usuario_id: uuid.UUID,
    tipo_saldo: TipoSaldo | None = None,
) -> int:
    #Suma lo que queda en los lotes que todavia no vencen.
 

    #Filtra por fecha y no por el campo estado para mayor seguridad del estado del token.
    sentencia = select(func.coalesce(func.sum(LoteDeTokens.cantidad_restante), 0)).where(
        LoteDeTokens.usuario_id == usuario_id,
        LoteDeTokens.fecha_vencimiento > ahora(),
    )
    if tipo_saldo is not None:
        sentencia = sentencia.where(LoteDeTokens.tipo_saldo == tipo_saldo)
    return int(db.execute(sentencia).scalar_one())

# ---------------------------------------------------------------------------
# Entradas
# ---------------------------------------------------------------------------
 
 
def otorgar(
    db: Session,
    usuario_id: uuid.UUID,
    cantidad: int,
    tipo_saldo: TipoSaldo,
    origen: OrigenLote,
    dias_vigencia: int,
    usuario_origen_id: uuid.UUID | None = None,
    retencion_id: uuid.UUID | None = None,
    tipo_transaccion: TipoTransaccion | None = None,
) -> LoteDeTokens:
    #Crea un lote nuevo y deja registrada la entrada.
 
    if cantidad <= 0:
        raise ValueError("La cantidad a otorgar debe ser mayor que cero")
 
    momento = ahora()
    saldo_previo = calcular_saldo(db, usuario_id)
 
    lote = LoteDeTokens(
        usuario_id=usuario_id,
        tipo_saldo=tipo_saldo,
        origen=origen,
        cantidad_original=cantidad,
        cantidad_restante=cantidad,
        fecha_recepcion=momento,
        fecha_vencimiento=momento + timedelta(days=dias_vigencia),     #Cada entrada genera su propio lote con su propia fecha de vencimiento
        estado=EstadoLote.VIGENTE,
    )
    db.add(lote)
    db.flush()  # asigna el id del lote
 
    db.add(
        Transaccion(
            usuario_origen_id=usuario_origen_id,
            usuario_destino_id=usuario_id,
            cantidad=cantidad,
            lote_id=lote.id,
            tipo=tipo_transaccion or _TIPO_TRANSACCION_POR_ORIGEN.get(origen, TipoTransaccion.ENTREGA),
            retencion_id=retencion_id,
            fecha=momento,
            saldo_resultante=saldo_previo + cantidad,
        )
    )
    db.flush()
    return lote


# ---------------------------------------------------------------------------
# Retenciones
# ---------------------------------------------------------------------------
 
 
def _lotes_consumibles(db: Session, usuario_id: uuid.UUID) -> list[LoteDeTokens]:

    #Lotes con saldo y sin vencer, en el orden en que se deben gastar.
    gratis_primero = case((LoteDeTokens.tipo_saldo == TipoSaldo.GRATIS, 0), else_=1)
    sentencia = (
        select(LoteDeTokens)
        .where(
            LoteDeTokens.usuario_id == usuario_id,
            LoteDeTokens.cantidad_restante > 0,
            LoteDeTokens.fecha_vencimiento > ahora(),
        )
        .order_by(LoteDeTokens.fecha_vencimiento, gratis_primero)
        .with_for_update()
    )
    return list(db.execute(sentencia).scalars())

def retener(
    db: Session,
    usuario_id: uuid.UUID,
    cantidad: int,
    solicitud_id: uuid.UUID | None = None,
) -> Retencion:
    #Saca tokens de los lotes del usuario y los deja apartados.
 
    if cantidad <= 0:
        raise ValueError("La cantidad a retener debe ser mayor que cero")
 
    lotes = _lotes_consumibles(db, usuario_id)
    disponible = sum(lote.cantidad_restante for lote in lotes)
    if disponible < cantidad:
        raise SaldoInsuficiente(disponible, cantidad)
 
    momento = ahora()
    retencion = Retencion(
        usuario_id=usuario_id,
        solicitud_id=solicitud_id,
        cantidad=cantidad,
        estado=EstadoRetencion.ACTIVA,
        fecha_creacion=momento,
    )
    db.add(retencion)
    db.flush()
 
    pendiente = cantidad
    saldo = disponible
    for lote in lotes:
        if pendiente == 0:
            break
        tomado = min(lote.cantidad_restante, pendiente)
        lote.cantidad_restante -= tomado
        if lote.cantidad_restante == 0:
            lote.estado = EstadoLote.AGOTADO
        pendiente -= tomado
        saldo -= tomado
 
        db.add(
            Transaccion(
                usuario_origen_id=usuario_id,
                usuario_destino_id=usuario_id,
                cantidad=tomado,
                lote_id=lote.id,
                tipo=TipoTransaccion.CONSUMO,
                retencion_id=retencion.id,
                fecha=momento,
                saldo_resultante=saldo,
            )
        )
 
    db.flush()
    return retencion

def _obtener_retencion_activa(db: Session, retencion_id: uuid.UUID) -> Retencion:

    #Bloquea la retencion para que liberar y reembolsar nunca ocurran los dos.
    retencion = db.get(Retencion, retencion_id, with_for_update=True)
    if retencion is None or retencion.estado != EstadoRetencion.ACTIVA:
        raise RetencionNoActiva()
    return retencion

def liberar(
    db: Session,
    retencion_id: uuid.UUID,
    tutor_id: uuid.UUID,
    motivo: str = "sesion completada",
) -> LoteDeTokens:

    retencion = _obtener_retencion_activa(db, retencion_id)
 
    lote = otorgar(
        db,
        usuario_id=tutor_id,
        cantidad=retencion.cantidad,
        tipo_saldo=TipoSaldo.PAGADO,
        origen=OrigenLote.PAGO_POR_ENSENAR,
        dias_vigencia=dias_de_vigencia(db, OrigenLote.PAGO_POR_ENSENAR),
        usuario_origen_id=retencion.usuario_id,
        retencion_id=retencion.id,
    )
 
    retencion.estado = EstadoRetencion.LIBERADA
    retencion.fecha_liberacion = ahora()
    retencion.motivo_resolucion = motivo
    db.flush()
    return lote

def reembolsar(db: Session, retencion_id: uuid.UUID, motivo: str) -> None:
    #Devuelve cada token retenido al lote exacto del que salio.
    retencion = _obtener_retencion_activa(db, retencion_id)
 
    consumos = db.execute(
        select(Transaccion).where(
            Transaccion.retencion_id == retencion.id,
            Transaccion.tipo == TipoTransaccion.CONSUMO,
        )
    ).scalars().all()
 
    momento = ahora()
    for consumo in consumos:
        lote = db.get(LoteDeTokens, consumo.lote_id, with_for_update=True)
     #Si ese lote vencio mientras los tokens estaban retenidos, se devuelven en un lote nuevo con el mismo tipo y origen
        if lote.fecha_vencimiento > momento:
            saldo_previo = calcular_saldo(db, retencion.usuario_id)
            lote.cantidad_restante += consumo.cantidad
            lote.estado = EstadoLote.VIGENTE
            db.add(
                Transaccion(
                    usuario_origen_id=None,
                    usuario_destino_id=retencion.usuario_id,
                    cantidad=consumo.cantidad,
                    lote_id=lote.id,
                    tipo=TipoTransaccion.REEMBOLSO,
                    retencion_id=retencion.id,
                    fecha=momento,
                    saldo_resultante=saldo_previo + consumo.cantidad,
                )
            )
            db.flush()
        else:
            otorgar(
                db,
                usuario_id=retencion.usuario_id,
                cantidad=consumo.cantidad,
                tipo_saldo=lote.tipo_saldo,
                origen=lote.origen,
                dias_vigencia=dias_de_vigencia(db, lote.origen),
                retencion_id=retencion.id,
                tipo_transaccion=TipoTransaccion.REEMBOLSO,
            )
 
    retencion.estado = EstadoRetencion.REEMBOLSADA
    retencion.fecha_liberacion = momento
    retencion.motivo_resolucion = motivo
    db.flush()
