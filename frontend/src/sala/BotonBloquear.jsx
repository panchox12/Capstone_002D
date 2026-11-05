import { useState } from 'react'
import { bloquearUsuario } from '../api/bloqueos'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { useSesion } from '../sesion/useSesion'
 
/** Bloquear a la otra persona, con una confirmacion antes. */
export function BotonBloquear({ usuarioId, nombre }) {
  const { token } = useSesion()
  const [paso, setPaso] = useState('inicio')
  const [error, setError] = useState(null)
 
  async function bloquear() {
    setError(null)
    try {
      await bloquearUsuario(token, usuarioId)
      setPaso('listo')
    } catch (e) {
      setError(e.message)
    }
  }
 
  if (paso === 'listo') {
    return (
      <Aviso tipo="exito" className="mt-4">
        Bloqueaste a {nombre}. Puedes deshacerlo en Mi cuenta.
      </Aviso>
    )
  }
  if (paso === 'confirmar') {
    return (
      <div className="mt-4">
        <p className="text-sm">¿Bloquear a {nombre}? No te podrá enviar solicitudes ni la verás en el buscador.</p>
        <div className="mt-2 flex gap-2">
          <Boton tamano="chico" onClick={bloquear}>
            Sí, bloquear
          </Boton>
          <Boton tamano="chico" variante="secundario" onClick={() => setPaso('inicio')}>
            No
          </Boton>
        </div>
        {error && (
          <Aviso tipo="error" className="mt-2">
            {error}
          </Aviso>
        )}
      </div>
    )
  }
  return (
    <Boton tamano="chico" variante="secundario" className="mt-4" onClick={() => setPaso('confirmar')}>
      Bloquear a {nombre}
    </Boton>
  )
}