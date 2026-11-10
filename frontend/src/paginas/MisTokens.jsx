import { useEffect, useState } from 'react'
import { obtenerMovimientos } from '../api/tokens'
import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from '../componentes/ui/Aviso'
import { BotonEnlace } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { diasHasta, fechaYHora, plural } from '../utilidades/formato'

const POR_ORIGEN = {
  entrega_semanal: 'Entrega semanal',
  video: 'Video visto',
  pago_por_ensenar: 'Cobraste una sesión',
}

const POR_TIPO = {
  consumo: 'Pagaste una sesión',
  compra: 'Compra de tokens',
  reembolso: 'Te devolvimos tokens',
  compensacion: 'Compensación por un reporte',
}

const NOMBRE_LOTE = {
  entrega_semanal: 'gratuitos',
  video: 'de videos',
  compra: 'comprados',
  pago_por_ensenar: 'ganados',
  compensacion: 'de compensación',
}

function titulo(movimiento) {
  if (movimiento.tipo === 'entrega') return POR_ORIGEN[movimiento.origen] ?? 'Entrada de tokens'
  return POR_TIPO[movimiento.tipo] ?? 'Movimiento'
}

function detalle(movimiento) {
  if (!movimiento.tema) return null
  return movimiento.contraparte ? `${movimiento.tema} · con ${movimiento.contraparte}` : movimiento.tema
}

function Cantidad({ valor }) {
  const entra = valor > 0
  return (
    <span className={`font-semibold whitespace-nowrap ${entra ? 'text-acierto' : 'text-tinta'}`}>
      {entra ? `+${valor}` : `−${Math.abs(valor)}`}
    </span>
  )
}

function TablaMovimientos({ movimientos }) {
  if (movimientos.length === 0) {
    return <p className="py-4 text-sm text-tinta/65">Todavía no tienes movimientos.</p>
  }
  return (
    <table className="w-full text-[13.5px]">
      <thead>
        <tr className="text-left text-[11px] tracking-widest text-tinta/60 uppercase">
          <th className="py-3 pr-3 font-normal">Fecha</th>
          <th className="py-3 pr-3 font-normal">Movimiento</th>
          <th className="py-3 pr-3 text-right font-normal">Tokens</th>
          <th className="hidden py-3 text-right font-normal sm:table-cell">Saldo</th>
        </tr>
      </thead>
      <tbody>
        {movimientos.map((movimiento) => (
          <tr key={`${movimiento.id}-${movimiento.tipo}`} className="border-t border-tinta/10 align-top">
            <td className="py-3.5 pr-3 whitespace-nowrap text-tinta/65">{fechaYHora(movimiento.fecha)}</td>
            <td className="py-3.5 pr-3">
              <p>{titulo(movimiento)}</p>
              {detalle(movimiento) && <p className="text-xs text-tinta/65">{detalle(movimiento)}</p>}
            </td>
            <td className="py-3.5 pr-3 text-right">
              <Cantidad valor={movimiento.cantidad} />
            </td>
            <td className="hidden py-3.5 text-right text-tinta/65 sm:table-cell">{movimiento.saldo_resultante}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function MisTokens() {
  const { token } = useSesion()
  const { saldo } = useSaldo()
  const [movimientos, setMovimientos] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let vigente = true
    obtenerMovimientos(token)
      .then((datos) => {
        if (vigente) setMovimientos(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [token])

  // Los lotes ya vienen ordenados del que vence antes al que vence despues
  const proximos = saldo?.lotes.slice(0, 3) ?? []

  return (
    <section className="grid items-start gap-5 lg:grid-cols-[1fr_320px]">
      <div>
        <TituloPagina
          titulo="Tus tokens"
          bajada="Todo lo que entró y salió de tu saldo: entregas, videos, compras, sesiones y devoluciones."
        />
        {error && (
          <Aviso tipo="error" className="mb-4">
            {error}
          </Aviso>
        )}
        <h2 className="mb-3 text-base">Historial</h2>
        <Tarjeta className="overflow-x-auto px-5 py-1">
          {movimientos === null ? (
            <p className="py-4 text-sm text-tinta/65">{error ? 'No se pudo cargar.' : 'Cargando…'}</p>
          ) : (
            <TablaMovimientos movimientos={movimientos} />
          )}
        </Tarjeta>
        <p className="mt-3 text-xs text-tinta/65">
          Al aceptar una solicitud los tokens quedan retenidos. Si la sesión no se hace, vuelven a tu saldo como
          devolución.
        </p>
      </div>

      <div className="flex flex-col gap-3.5">
        {saldo && (
          <Tarjeta>
            <h2 className="mb-2 text-[13.5px] font-semibold tracking-normal">Tu saldo</h2>
            <dl className="grid grid-cols-[1fr_auto] gap-y-2 text-sm">
              <dt className="text-tinta/65">Gratuito</dt>
              <dd className="text-right font-semibold">{saldo.gratis}</dd>
              <dt className="text-tinta/65">Pagado</dt>
              <dd className="text-right font-semibold">{saldo.pagado}</dd>
              <dt className="text-tinta/65">Retenidos</dt>
              <dd className="text-right font-semibold">{saldo.retenidos}</dd>
              <dt className="border-t border-tinta/15 pt-2.5">Disponible</dt>
              <dd className="border-t border-tinta/15 pt-2.5 text-right font-extrabold">{saldo.total}</dd>
            </dl>
          </Tarjeta>
        )}
        {proximos.length > 0 && (
          <Tarjeta>
            <h2 className="mb-2 text-[13.5px] font-semibold tracking-normal">Próximos a vencer</h2>
            <ul className="flex flex-col gap-2 text-sm">
              {proximos.map((lote) => (
                <li key={lote.id} className="flex justify-between gap-3">
                  <span>
                    {plural(lote.cantidad_restante, 'token', 'tokens')} {NOMBRE_LOTE[lote.origen] ?? ''}
                  </span>
                  <span className="text-tinta/65">en {plural(diasHasta(lote.fecha_vencimiento), 'día', 'días')}</span>
                </li>
              ))}
            </ul>
          </Tarjeta>
        )}
        <BotonEnlace to="/tienda" variante="secundario" className="w-full">
          Recargar tokens
        </BotonEnlace>
      </div>
    </section>
  )
}