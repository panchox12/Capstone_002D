import { useEffect, useState } from 'react'
import { obtenerMiValoracion, valorarSesion } from '../api/valoraciones'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { claseCampo, claseEtiqueta } from '../componentes/ui/clases'
import { useSesion } from '../sesion/useSesion'
 
const ESTRELLAS = [1, 2, 3, 4, 5]
 
function Estrellas({ valor, alElegir }) {
  return (
    <div role="radiogroup" aria-label="Estrellas" className="flex gap-1">
      {ESTRELLAS.map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={valor === n}
          aria-label={`${n} ${n === 1 ? 'estrella' : 'estrellas'}`}
          disabled={!alElegir}
          onClick={() => alElegir?.(n)}
          className={`text-2xl leading-none ${n <= valor ? 'text-oceano' : 'text-bruma'} disabled:cursor-default`}
        >
          ★
        </button>
      ))}
    </div>
  )
}
 
/** Valoracion voluntaria de la otra persona al terminar la sesion. */
export function Valorar({ sesionId, nombre }) {
  const { token } = useSesion()
  const [estado, setEstado] = useState(null)
  const [estrellas, setEstrellas] = useState(0)
  const [comentario, setComentario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
 
  useEffect(() => {
    let vigente = true
    obtenerMiValoracion(token, sesionId)
      .then((datos) => {
        if (vigente) setEstado(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [token, sesionId])
 
  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      const valoracion = await valorarSesion(token, sesionId, estrellas, comentario || null)
      setEstado({ valorada: true, valoracion })
    } catch (e) {
      setError(e.message)
    } finally {
      setEnviando(false)
    }
  }
 
  if (estado === null) return error ? <Aviso tipo="error">{error}</Aviso> : null
 
  if (estado.valorada) {
    return (
      <div className="mt-4">
        <p className="text-sm font-semibold">Tu valoración de {nombre}</p>
        <Estrellas valor={estado.valoracion.estrellas} />
      </div>
    )
  }
 
  return (
    <form onSubmit={enviar} className="mt-4 grid gap-3">
      <p className="text-sm font-semibold">¿Cómo te fue con {nombre}? Es voluntario.</p>
      <Estrellas valor={estrellas} alElegir={setEstrellas} />
      <label className={claseEtiqueta}>
        Comentario (opcional)
        <textarea
          className={claseCampo}
          rows={2}
          maxLength={500}
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
        />
      </label>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <Boton type="submit" tamano="chico" className="justify-self-start" disabled={estrellas === 0 || enviando}>
        Enviar valoración
      </Boton>
    </form>
  )
}