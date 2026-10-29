import { useEffect, useState } from 'react'
import { guardarPreferencias, obtenerPreferencias } from '../api/perfiles'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from './ui/Aviso'
import { Tarjeta } from './ui/Tarjeta'

const OPCIONES = [
  {
    clave: 'mostrar_en_linea',
    titulo: 'Aparecer como conectado',
    ayuda: 'Si lo apagas, sigues usando Cachai pero nadie te ve en línea. Las solicitudes te llegan como diferidas.',
  },
  {
    clave: 'acepta_diferidas',
    titulo: 'Recibir solicitudes estando fuera',
    ayuda: 'Te pueden escribir aunque no estés conectado. Tienes 24 horas para responder.',
  },
]

// Interruptores de presencia. Cada cambio se guarda al tiro.
export function Preferencias() {
  const { token } = useSesion()
  const [valores, setValores] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let vigente = true
    obtenerPreferencias(token)
      .then((datos) => {
        if (vigente) setValores(datos)
      })
      .catch(() => {})
    return () => {
      vigente = false
    }
  }, [token])

  async function cambiar(clave, activo) {
    setError(null)
    try {
      setValores(await guardarPreferencias(token, { [clave]: activo }))
    } catch (e) {
      setError(e.message)
    }
  }

  if (!valores) return null

  return (
    <Tarjeta className="mt-4 p-6">
      <h2 className="mb-3 text-[17px]">Presencia</h2>
      <div className="grid gap-4">
        {OPCIONES.map((opcion) => (
          <label key={opcion.clave} className="flex items-start gap-3">
            <input
              type="checkbox"
              role="switch"
              checked={valores[opcion.clave]}
              onChange={(e) => cambiar(opcion.clave, e.target.checked)}
              aria-labelledby={`titulo-${opcion.clave}`}
              aria-describedby={`ayuda-${opcion.clave}`}
              className="mt-1 size-4 accent-oceano"
            />
            <span>
              <span id={`titulo-${opcion.clave}`} className="block text-sm font-semibold">
                {opcion.titulo}
              </span>
              <span id={`ayuda-${opcion.clave}`} className="block text-xs text-tinta/65">
                {opcion.ayuda}
              </span>
            </span>
          </label>
        ))}
      </div>
      {error && (
        <Aviso tipo="error" className="mt-3">
          {error}
        </Aviso>
      )}
    </Tarjeta>
  )
}