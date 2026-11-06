import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { marcarLeida, marcarTodasLeidas, obtenerNotificaciones } from '../api/notificaciones'
import { useSesion } from '../sesion/useSesion'
import { Boton } from './ui/Boton'
 
// La campana se revisa cada 30 segundos, igual que el latido de presencia.
const MILISEGUNDOS_ENTRE_REVISIONES = 30_000
 
/** Campana con los avisos del usuario. Si la API falla, simplemente no muestra nada. */
export function Campana() {
  const { token } = useSesion()
  const navegar = useNavigate()
  const [bandeja, setBandeja] = useState(null)
  const [abierta, setAbierta] = useState(false)
 
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
    <div className="relative">
      <button
        type="button"
        aria-label={etiqueta}
        aria-expanded={abierta}
        onClick={() => setAbierta((a) => !a)}
        className="relative rounded-full p-2 text-lg leading-none hover:bg-tinta/5"
      >
        🔔
        {bandeja.no_leidas > 0 && (
          <span className="absolute -top-0.5 -right-0.5 rounded-full bg-alerta px-1.5 text-[10.5px] font-semibold text-white">
            {bandeja.no_leidas}
          </span>
        )}
      </button>
      {abierta && (
        <div className="absolute right-0 z-10 mt-2 w-80 rounded-tarjeta bg-white p-3 shadow-flotante">
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