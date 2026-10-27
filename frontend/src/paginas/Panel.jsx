import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { TarjetaVideo } from '../componentes/TarjetaVideo'
import { Aviso } from '../componentes/ui/Aviso'
import { BotonEnlace } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { diasHasta, plural } from '../utilidades/formato'

function TarjetaGratis({ saldo }) {
  const lotes = saldo.lotes.filter((lote) => lote.tipo_saldo === 'gratis')
  const porcentaje = Math.min(100, Math.round((saldo.gratis / saldo.tope_saldo_gratis) * 100))

  return (
    <Tarjeta variante="celeste" className="flex-1 px-6 py-5">
      <p className="flex items-baseline gap-2">
        <span className="font-titulo text-[40px] leading-none font-extrabold">{saldo.gratis}</span>
        <span className="text-[13.5px] font-semibold">tokens gratuitos</span>
      </p>
      <div className="mt-3.5 mb-2 h-2.5 rounded-full bg-abismo/15" aria-hidden="true">
        <div className="h-full rounded-full bg-oceano" style={{ width: `${porcentaje}%` }} />
      </div>
      <p className="text-xs opacity-85">
        Vuelven a {saldo.tope_saldo_gratis} el lunes
        {lotes.length > 0 && ` · vencen en ${plural(diasHasta(lotes[0].fecha_vencimiento), 'día', 'días')}`}
      </p>
    </Tarjeta>
  )
}

function TarjetaPagados({ saldo }) {
  const lotes = saldo.lotes.filter((lote) => lote.tipo_saldo === 'pagado')
  // Un segmento por lote: el mas oscuro es el que vence antes
  const tonos = ['bg-grafito', 'bg-ceniza', 'bg-bruma']

  return (
    <Tarjeta variante="gris" className="flex-1 px-6 py-5">
      <p className="flex items-baseline gap-2">
        <span className="font-titulo text-[40px] leading-none font-extrabold">{saldo.pagado}</span>
        <span className="text-[13.5px] font-semibold">tokens pagados</span>
      </p>
      <div className="mt-3.5 mb-2 flex h-2.5 gap-1.5" aria-hidden="true">
        {lotes.length === 0 ? (
          <span className="flex-1 rounded-full bg-bruma" />
        ) : (
          lotes.map((lote, i) => (
            <span
              key={lote.id}
              className={`rounded-full ${tonos[Math.min(i, tonos.length - 1)]}`}
              style={{ flexGrow: lote.cantidad_restante }}
            />
          ))
        )}
      </div>
      <p className="text-xs text-tinta/65">
        {lotes.length === 0
          ? 'Sin tokens pagados por ahora'
          : `${plural(lotes.length, 'lote', 'lotes')} · el más cercano vence en ${plural(diasHasta(lotes[0].fecha_vencimiento), 'día', 'días')}`}
      </p>
    </Tarjeta>
  )
}

// Inicio de quien tiene sesion.
export function Panel() {
  const { usuario } = useSesion()
  const { saldo } = useSaldo()
  const primerNombre = usuario.nombre_visible.split(' ')[0]

  return (
    <section className="grid items-start gap-5 lg:grid-cols-[1fr_300px]">
      <div>
        <h1 className="text-[31px] leading-tight">Hola {primerNombre}, ¿qué duda resolvemos hoy?</h1>
        <p className="mt-1 mb-5 text-sm text-tinta/65">Los tokens gratuitos se renuevan cada lunes.</p>

        {usuario.estado_cuenta !== 'activa' && (
          <Aviso tipo="info">Confirma tu correo para ver tu saldo y empezar a usar Cachai.</Aviso>
        )}

        {saldo && (
          <>
            <div className="flex flex-col gap-3.5 sm:flex-row">
              <TarjetaGratis saldo={saldo} />
              <TarjetaPagados saldo={saldo} />
            </div>
            {saldo.retenidos > 0 && (
              <Aviso tipo="neutro" className="mt-4">
                Tienes {plural(saldo.retenidos, 'token retenido', 'tokens retenidos')} en tus solicitudes. Retenido no
                es gastado: vuelven si la solicitud se rechaza, vence o la cancelas.
              </Aviso>
            )}
          </>
        )}
      </div>

      <div className="flex flex-col gap-3.5">
        <TarjetaVideo />
        <Tarjeta variante="oceano">
          <h2 className="mb-1.5 text-[15px] text-white">Enseña lo que sabes</h2>
          <p className="mb-3.5 text-[12.5px] opacity-90">
            Publica una habilidad con tu precio y empieza a recibir tokens.
          </p>
          <BotonEnlace to="/temas" variante="invertido" tamano="chico">
            Ver los temas
          </BotonEnlace>
        </Tarjeta>
        <Tarjeta variante="gris" className="text-xs leading-relaxed text-tinta/65">
          Todas las sesiones se graban y la grabación se borra a las 24 horas.
        </Tarjeta>
      </div>
    </section>
  )
}