import { useEffect, useState } from 'react'
import { desbloquearUsuario, obtenerBloqueados } from '../api/bloqueos'
import { useSesion } from '../sesion/useSesion'
import { fechaCorta } from '../utilidades/formato'
import { Aviso } from './ui/Aviso'
import { Boton } from './ui/Boton'
import { Tarjeta } from './ui/Tarjeta'
 
/** Personas bloqueadas, con la opcion de desbloquear. Va en Mi cuenta. */
export function Bloqueados() {
  const { token } = useSesion()
  const [lista, setLista] = useState(null)
  const [error, setError] = useState(null)
 
  useEffect(() => {
    let vigente = true
    obtenerBloqueados(token)
      .then((datos) => {
        if (vigente) setLista(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [token])
 
  async function desbloquear(usuarioId) {
    setError(null)
    try {
      await desbloquearUsuario(token, usuarioId)
      setLista((actual) => actual.filter((fila) => fila.usuario_id !== usuarioId))
    } catch (e) {
      setError(e.message)
    }
  }
 
  return (
    <Tarjeta className="mt-4 p-6">
      <h2 className="text-base">Personas bloqueadas</h2>
      <p className="mt-1 text-xs text-tinta/65">No te pueden escribir y no las ves en el buscador.</p>
      {error && (
        <Aviso tipo="error" className="mt-3">
          {error}
        </Aviso>
      )}
      {lista !== null && lista.length === 0 && <p className="mt-3 text-sm text-tinta/65">No has bloqueado a nadie.</p>}
      {lista !== null && lista.length > 0 && (
        <ul className="mt-3 grid gap-2">
          {lista.map((fila) => (
            <li key={fila.usuario_id} className="flex items-center gap-3">
              <span className="mr-auto text-sm">
                {fila.nombre_visible} <span className="text-xs text-tinta/65">desde {fechaCorta(fila.desde)}</span>
              </span>
              <Boton tamano="chico" variante="secundario" onClick={() => desbloquear(fila.usuario_id)}>
                Desbloquear
              </Boton>
            </li>
          ))}
        </ul>
      )}
    </Tarjeta>
  )
}