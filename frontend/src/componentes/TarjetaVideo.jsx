import { useCallback, useEffect, useState } from 'react'
import { registrarVideo } from '../api/tokens'
import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { plural } from '../utilidades/formato'
import { Aviso } from './ui/Aviso'
import { Boton } from './ui/Boton'
import { Tarjeta } from './ui/Tarjeta'

export const SEGUNDOS_DE_ANUNCIO = 30

// Video publicitario simulado con una cuenta regresiva.
export function TarjetaVideo() {
  const { token } = useSesion()
  const { saldo, actualizar } = useSaldo()
  const [restantes, setRestantes] = useState(null)
  const [mensaje, setMensaje] = useState(null)

  const terminar = useCallback(async () => {
    try {
      const resultado = await registrarVideo(token)
      setMensaje({
        tipo: 'exito',
        texto: `Sumaste ${plural(resultado.tokens_otorgados, 'token gratuito', 'tokens gratuitos')}.`,
      })
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e.message })
    } finally {
      setRestantes(null)
      actualizar()
    }
  }, [token, actualizar])

  // Baja un segundo a la vez; al llegar a cero se registra el video.
  useEffect(() => {
    if (restantes === null) return undefined
    const espera = setTimeout(() => {
      if (restantes > 1) setRestantes(restantes - 1)
      else terminar()
    }, 1000)
    return () => clearTimeout(espera)
  }, [restantes, terminar])

  if (!saldo) return null

  const vistos = saldo.videos_vistos_hoy
  const tope = saldo.tope_videos_por_dia
  const agotados = vistos >= tope
  const lleno = saldo.gratis >= saldo.tope_saldo_gratis
  const viendo = restantes !== null

  let textoBoton = `Ver video · ${SEGUNDOS_DE_ANUNCIO} seg`
  if (agotados) textoBoton = 'Vuelve mañana por más videos'
  else if (lleno) textoBoton = 'Tu saldo gratuito está completo'

  function empezar() {
    setMensaje(null)
    setRestantes(SEGUNDOS_DE_ANUNCIO)
  }

  return (
    <Tarjeta>
      <h2 className="mb-2.5 text-[13.5px] font-semibold tracking-normal">¿Sin tokens? Mira un video</h2>
      <p className="flex items-baseline gap-2">
        <span className="font-titulo text-[30px] leading-none font-extrabold">{vistos}</span>
        <span className="text-[12.5px] text-tinta/65">de {tope} hoy</span>
      </p>
      <div className="my-3 flex gap-1.5" aria-hidden="true">
        {Array.from({ length: tope }, (_, i) => (
          <span key={i} className={`h-2 flex-1 rounded-full ${i < vistos ? 'bg-oceano' : 'bg-bruma'}`} />
        ))}
      </div>

      {viendo ? (
        <div role="status" className="rounded-2xl bg-tinta px-4 py-5 text-center text-white">
          <p className="text-[11px] tracking-widest uppercase opacity-70">Anuncio</p>
          <p className="mt-1 font-reloj text-2xl">{restantes} s</p>
          <p className="mt-1 text-xs opacity-80">Tu token llega cuando termine el video</p>
        </div>
      ) : (
        <Boton className="w-full" disabled={agotados || lleno} onClick={empezar}>
          {textoBoton}
        </Boton>
      )}

      {mensaje && (
        <Aviso tipo={mensaje.tipo} className="mt-3">
          {mensaje.texto}
        </Aviso>
      )}
    </Tarjeta>
  )
}