import { useEffect, useState } from 'react'
import { actualizarHabilidad, obtenerMisHabilidades, publicarHabilidad } from '../api/habilidades'
import { obtenerCatalogo } from '../api/temas'
import { useSesion } from '../sesion/useSesion'
import { plural } from '../utilidades/formato'
import { Aviso } from './ui/Aviso'
import { Boton, BotonEnlace } from './ui/Boton'
import { claseCampo, claseEtiqueta } from './ui/clases'
import { Ficha } from './ui/Ficha'
import { Tarjeta } from './ui/Tarjeta'
 
function FilaHabilidad({ habilidad, verificado, alCambiar }) {
  const [precio, setPrecio] = useState(String(habilidad.precio_por_bloque))
  const [editando, setEditando] = useState(false)
  const publicada = habilidad.estado === 'publicada'
 
  async function guardarPrecio(evento) {
    evento.preventDefault()
    const listo = await alCambiar(habilidad.id, { precio_por_bloque: Number(precio) })
    if (listo) setEditando(false)
  }
 
  return (
    <li className="border-t border-tinta/10 py-3 first:border-t-0">
      <div className="flex flex-wrap items-center gap-3">
        <div className="mr-auto">
          <p className="text-sm font-semibold">{habilidad.tema_nombre}</p>
          <p className="text-xs text-tinta/65">{plural(habilidad.precio_por_bloque, 'token', 'tokens')} por bloque</p>
        </div>
        <Ficha variante={publicada ? 'celeste' : 'gris'}>{publicada ? 'Publicada' : 'Pausada'}</Ficha>
        {verificado && (
          <>
            <Boton
              tamano="chico"
              variante="secundario"
              onClick={() => setEditando(!editando)}
              aria-label={`Cambiar precio de ${habilidad.tema_nombre}`}
            >
              Cambiar precio
            </Boton>
            <Boton
              tamano="chico"
              variante="secundario"
              onClick={() => alCambiar(habilidad.id, { estado: publicada ? 'pausada' : 'publicada' })}
              aria-label={`${publicada ? 'Pausar' : 'Publicar'} ${habilidad.tema_nombre}`}
            >
              {publicada ? 'Pausar' : 'Publicar'}
            </Boton>
          </>
        )}
      </div>
      {editando && (
        <form onSubmit={guardarPrecio} className="mt-3 flex flex-wrap items-end gap-3">
          <label className={claseEtiqueta}>
            Nuevo precio por bloque
            <input
              type="number"
              min="1"
              required
              value={precio}
              onChange={(e) => setPrecio(e.target.value)}
              className={claseCampo}
            />
          </label>
          <Boton type="submit" tamano="chico">
            Guardar precio
          </Boton>
        </form>
      )}
    </li>
  )
}
 
// Solo se publican temas del nivel 3: el arbol se agrupa por area y materia.
function GruposDeTemas({ catalogo, ofrecidos }) {
  return catalogo.flatMap((area) =>
    area.hijos.map((materia) => (
      <optgroup key={materia.id} label={`${area.nombre} · ${materia.nombre}`}>
        {materia.hijos.map((tema) => (
          <option key={tema.id} value={tema.id} disabled={ofrecidos.has(tema.id)}>
            {tema.nombre}
          </option>
        ))}
      </optgroup>
    )),
  )
}
 
// Habilidades que enseña la persona, con su precio. Va en Mi cuenta.
export function MisHabilidades({ verificado }) {
  const { token } = useSesion()
  const [habilidades, setHabilidades] = useState(null)
  const [catalogo, setCatalogo] = useState([])
  const [temaId, setTemaId] = useState('')
  const [precio, setPrecio] = useState('1')
  const [publicando, setPublicando] = useState(false)
  const [error, setError] = useState(null)
 
  useEffect(() => {
    let vigente = true
    Promise.all([obtenerMisHabilidades(token), obtenerCatalogo()])
      .then(([mias, temas]) => {
        if (!vigente) return
        setHabilidades(mias)
        setCatalogo(temas)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [token])
 
  async function publicar(evento) {
    evento.preventDefault()
    setError(null)
    setPublicando(true)
    try {
      const nueva = await publicarHabilidad(token, Number(temaId), Number(precio))
      setHabilidades((actuales) => [...actuales, nueva])
      setTemaId('')
      setPrecio('1')
    } catch (e) {
      setError(e.message)
    } finally {
      setPublicando(false)
    }
  }
 
  // Devuelve si se guardo, para que la fila sepa si cierra su formulario.
  async function cambiar(habilidadId, cambios) {
    setError(null)
    try {
      const nueva = await actualizarHabilidad(token, habilidadId, cambios)
      setHabilidades((actuales) => actuales.map((fila) => (fila.id === habilidadId ? nueva : fila)))
      return true
    } catch (e) {
      setError(e.message)
      return false
    }
  }
 
  const ofrecidos = new Set((habilidades ?? []).map((fila) => fila.tema_id))
 
  return (
    <Tarjeta className="mt-4 p-6">
      <h2 className="text-[17px]">Mis habilidades</h2>
      <p className="mt-1 text-xs text-tinta/65">El precio se define por habilidad, no por persona.</p>
 
      {error && (
        <Aviso tipo="error" className="mt-3">
          {error}
        </Aviso>
      )}
 
      {habilidades !== null && habilidades.length === 0 && (
        <p className="mt-3 text-sm text-tinta/65">Todavía no ofreces ninguna habilidad.</p>
      )}
      {habilidades !== null && habilidades.length > 0 && (
        <ul className="mt-3">
          {habilidades.map((habilidad) => (
            <FilaHabilidad key={habilidad.id} habilidad={habilidad} verificado={verificado} alCambiar={cambiar} />
          ))}
        </ul>
      )}
 
      {!verificado && habilidades !== null && (
        <div className="mt-4">
          <p className="mb-3 text-sm text-tinta/80">Para enseñar necesitas verificar tu identidad.</p>
          <BotonEnlace to="/verificar" tamano="chico">
            Verificar ahora
          </BotonEnlace>
        </div>
      )}
 
      {verificado && habilidades !== null && (
        <form onSubmit={publicar} className="mt-4 grid gap-3 border-t border-tinta/10 pt-4">
          <h3 className="text-[15px]">Agregar habilidad</h3>
          <label className={claseEtiqueta}>
            Tema
            <select required value={temaId} onChange={(e) => setTemaId(e.target.value)} className={claseCampo}>
              <option value="">Elige un tema</option>
              <GruposDeTemas catalogo={catalogo} ofrecidos={ofrecidos} />
            </select>
          </label>
          <label className={claseEtiqueta}>
            Precio por bloque de 15 minutos, en tokens
            <input
              type="number"
              min="1"
              required
              value={precio}
              onChange={(e) => setPrecio(e.target.value)}
              className={claseCampo}
            />
          </label>
          <Boton type="submit" tamano="chico" disabled={publicando || !temaId} className="justify-self-start">
            {publicando ? 'Publicando…' : 'Publicar habilidad'}
          </Boton>
        </form>
      )}
    </Tarjeta>
  )
}