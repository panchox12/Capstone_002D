import { useCallback, useEffect, useState } from 'react'
import { comprarPaquete, obtenerCompras, obtenerPaquetes } from '../api/tienda'
import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { TarjetaVideo } from '../componentes/TarjetaVideo'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { fechaCorta, pesos } from '../utilidades/formato'

const NOMBRES = { basico: 'Básico', popular: 'Más elegido', volumen: 'Volumen' }
const DESTACADO = 'popular'

function EstadoCompra({ compra }) {
  if (compra.vencida && compra.tokens_restantes > 0) {
    return (
      <Ficha variante="contorno" className="whitespace-nowrap">
        {compra.tokens_restantes} vencidos
      </Ficha>
    )
  }
  if (compra.tokens_restantes === 0) {
    return (
      <Ficha variante="gris" className="whitespace-nowrap">
        Consumido
      </Ficha>
    )
  }
  return <Ficha className="whitespace-nowrap">{compra.tokens_restantes} restantes</Ficha>
}

function TarjetaPaquete({ paquete, comprando, alComprar }) {
  const destacado = paquete.codigo === DESTACADO
  return (
    <Tarjeta variante={destacado ? 'celeste' : 'blanca'} como="article" className="flex flex-col p-6">
      <h2 className="text-[11px] font-semibold tracking-widest text-oceano-oscuro uppercase">
        {NOMBRES[paquete.codigo]}
      </h2>
      <p className="mt-2 font-titulo text-[48px] leading-none font-extrabold">{paquete.cantidad_tokens}</p>
      <p className="text-[13px] text-tinta/65">tokens</p>
      <p className="mt-4 font-titulo text-[21px] font-extrabold">{pesos(paquete.monto_pesos)}</p>
      <p className="mb-4 text-xs text-tinta/65">{paquete.pesos_por_token} pesos por token</p>
      <Boton
        variante={destacado ? 'primario' : 'secundario'}
        className="mt-auto w-full"
        disabled={comprando !== null}
        onClick={() => alComprar(paquete)}
        aria-label={`Comprar ${paquete.cantidad_tokens} tokens`}
      >
        {comprando === paquete.codigo ? 'Comprando…' : 'Comprar'}
      </Boton>
    </Tarjeta>
  )
}

export function Tienda() {
  const { token } = useSesion()
  const { saldo, actualizar } = useSaldo()
  const [paquetes, setPaquetes] = useState([])
  const [compras, setCompras] = useState([])
  const [comprando, setComprando] = useState(null)
  const [mensaje, setMensaje] = useState(null)

  const cargarCompras = useCallback(() => obtenerCompras(token).then(setCompras), [token])

  useEffect(() => {
    obtenerPaquetes()
      .then(setPaquetes)
      .catch((e) => setMensaje({ tipo: 'error', texto: e.message }))
    cargarCompras().catch(() => {})
  }, [cargarCompras])

  async function comprar(paquete) {
    setMensaje(null)
    setComprando(paquete.codigo)
    try {
      await comprarPaquete(token, paquete.codigo)
      setMensaje({ tipo: 'exito', texto: `Listo: sumaste ${paquete.cantidad_tokens} tokens (pago simulado).` })
      await Promise.all([actualizar(), cargarCompras()])
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e.message })
    } finally {
      setComprando(null)
    }
  }

  return (
    <section className="grid items-start gap-5 lg:grid-cols-[1fr_320px]">
      <div>
        <TituloPagina
          titulo="Recarga cuando quieras"
          bajada="Sin suscripción y sin cobros automáticos. Compras cuando lo necesitas, y lo que compras dura 30 días."
        />

        <div className="grid gap-3.5 sm:grid-cols-3">
          {paquetes.map((paquete) => (
            <TarjetaPaquete key={paquete.codigo} paquete={paquete} comprando={comprando} alComprar={comprar} />
          ))}
        </div>
        <p className="mt-3 text-xs text-tinta/65">
          Cada compra crea un lote propio con su fecha de vencimiento. Al gastar se consume siempre el lote que vence
          antes.
        </p>
        {mensaje && (
          <Aviso tipo={mensaje.tipo} className="mt-4">
            {mensaje.texto}
          </Aviso>
        )}

        <h2 className="mt-8 mb-3 text-base">Historial de compras</h2>
        <Tarjeta className="overflow-x-auto px-5 py-1">
          {compras.length === 0 ? (
            <p className="py-4 text-sm text-tinta/65">Todavía no has comprado tokens.</p>
          ) : (
            <table className="w-full text-[13.5px]">
              <thead>
                <tr className="text-left text-[11px] tracking-widest text-tinta/60 uppercase">
                  <th className="py-3 pr-3 font-normal">Fecha</th>
                  <th className="hidden py-3 pr-3 font-normal sm:table-cell">Paquete</th>
                  <th className="py-3 pr-3 font-normal">Monto</th>
                  <th className="hidden py-3 pr-3 font-normal sm:table-cell">Vence</th>
                  <th className="py-3 text-right font-normal">Estado</th>
                </tr>
              </thead>
              <tbody>
                {compras.map((compra) => (
                  <tr key={compra.id} className="border-t border-tinta/10">
                    <td className="py-3.5 pr-3">{fechaCorta(compra.fecha)}</td>
                    <td className="hidden py-3.5 pr-3 text-tinta/65 sm:table-cell">{compra.cantidad_tokens} tokens</td>
                    <td className="py-3.5 pr-3">{pesos(compra.monto_pesos)}</td>
                    <td className="hidden py-3.5 pr-3 text-tinta/65 sm:table-cell">
                      {compra.fecha_vencimiento ? fechaCorta(compra.fecha_vencimiento) : '—'}
                    </td>
                    <td className="py-3.5 text-right">
                      <EstadoCompra compra={compra} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Tarjeta>
      </div>

      <div className="flex flex-col gap-3.5">
        <TarjetaVideo />
        {saldo && (
          <Tarjeta>
            <h2 className="mb-2 text-[13.5px] font-semibold tracking-normal">Tu saldo</h2>
            <dl className="grid grid-cols-[1fr_auto] gap-y-2 text-sm">
              <dt className="text-tinta/65">Gratuito</dt>
              <dd className="text-right font-semibold">{saldo.gratis}</dd>
              <dt className="text-tinta/65">Pagado</dt>
              <dd className="text-right font-semibold">{saldo.pagado}</dd>
              <dt className="border-t border-tinta/15 pt-2.5">Total</dt>
              <dd className="border-t border-tinta/15 pt-2.5 text-right font-extrabold">{saldo.total}</dd>
            </dl>
          </Tarjeta>
        )}
        <Tarjeta variante="gris" className="text-xs leading-relaxed text-tinta/65">
          Los tokens no se pueden retirar como dinero, regalar ni transferir. Solo cambian de dueño a través de una
          sesión completada.
        </Tarjeta>
      </div>
    </section>
  )
}