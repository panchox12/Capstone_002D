import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { marcarLeida, marcarTodasLeidas, obtenerNotificaciones } from '../api/notificaciones'
import { useSesion } from '../sesion/useSesion'
import { tocar } from '../sonido/sonidos'
import { Boton } from './ui/Boton'

// La campana se revisa cada 30 segundos, igual que el latido de presencia.
const MILISEGUNDOS_ENTRE_REVISIONES = 30_000

function IconoCampana() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  )
}

/** Campana con los avisos del usuario. Si la API falla, simplemente no muestra nada. */
export function Campana() {
  const { token } = useSesion()
  const navegar = useNavigate()
  const [bandeja, setBandeja] = useState(null)
  const [abierta, setAbierta] = useState(false)
  const anteriores = useRef(null)
  const caja = useRef(null)

  const cargar = useCallback(
    () =>
      obtenerNotificaciones(token)
        .then(setBandeja)
        .catch(() => {}),
    [token],
  )

  useEffect(() => {
    cargar()
    const revision = setInterval(cargar, MILISEGUNDOS_ENTRE_REVISIONES)
    return () => clearInterval(revision)
  }, [cargar])

  // Suena solo cuando llegan avisos nuevos, no al abrir la página
  useEffect(() => {
    if (!bandeja) return
    if (anteriores.current !== null && bandeja.no_leidas > anteriores.current) tocar('aviso')
    anteriores.current = bandeja.no_leidas
  }, [bandeja])

  // El panel se cierra al tocar fuera o con Escape
  useEffect(() => {
    if (!abierta) return undefined
    const fuera = (evento) => {
      if (caja.current && !caja.current.contains(evento.target)) setAbierta(false)
    }
    const escape = (evento) => {
      if (evento.key === 'Escape') setAbierta(false)
    }
    document.addEventListener('pointerdown', fuera)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('pointerdown', fuera)
      document.removeEventListener('keydown', escape)
    }
  }, [abierta])

  async function abrirAviso(aviso) {
    setAbierta(false)
    if (!aviso.leida) await marcarLeida(token, aviso.id).catch(() => {})
    cargar()
    if (aviso.enlace) navegar(aviso.enlace)
  }

  async function leerTodas() {
    await marcarTodasLeidas(token).catch(() => {})
    cargar()
  }

  if (bandeja === null) return null
  const etiqueta = bandeja.no_leidas ? `Avisos, ${bandeja.no_leidas} sin leer` : 'Avisos'

  return (
    <div className="relative" ref={caja}>
      <button
        type="button"
        aria-label={etiqueta}
        aria-expanded={abierta}
        onClick={() => setAbierta((a) => !a)}
        className="relative grid place-items-center rounded-full p-2 text-tinta hover:bg-tinta/5"
      >
        <IconoCampana />
        {bandeja.no_leidas > 0 && (
          <span className="absolute -top-0.5 -right-0.5 rounded-full bg-alerta px-1.5 text-[10.5px] font-semibold text-white">
            {bandeja.no_leidas}
          </span>
        )}
      </button>
      {abierta && (
        // En el teléfono el panel ocupa el ancho de la pantalla; desde sm cuelga de la campana
        <div className="fixed inset-x-4 top-16 z-20 rounded-tarjeta bg-white p-3 shadow-flotante sm:absolute sm:inset-x-auto sm:top-auto sm:right-0 sm:mt-2 sm:w-80">
          <div className="mb-2 flex items-center">
            <p className="mr-auto text-sm font-semibold">Avisos</p>
            {bandeja.no_leidas > 0 && (
              <Boton tamano="chico" variante="secundario" onClick={leerTodas}>
                Marcar todo leído
              </Boton>
            )}
          </div>
          {bandeja.avisos.length === 0 ? (
            <p className="text-sm text-tinta/65">No tienes avisos.</p>
          ) : (
            <ul className="grid max-h-96 gap-1 overflow-y-auto">
              {bandeja.avisos.map((aviso) => (
                <li key={aviso.id}>
                  <button
                    type="button"
                    onClick={() => abrirAviso(aviso)}
                    className={`w-full rounded-xl px-3 py-2 text-left hover:bg-niebla ${aviso.leida ? '' : 'bg-celeste/60'}`}
                  >
                    <span className="block text-[13px] font-semibold">{aviso.titulo}</span>
                    <span className="block text-xs text-tinta/75">{aviso.mensaje}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}