import { useEffect, useState } from 'react'
import { guardarPerfil, obtenerPerfil } from '../api/perfiles'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from './ui/Aviso'
import { Boton, BotonEnlace } from './ui/Boton'
import { claseCampo, claseEtiqueta } from './ui/clases'
import { Tarjeta } from './ui/Tarjeta'
 
const LARGO_BIOGRAFIA = 500
 
// Biografia y alias del perfil publico. Va en Mi cuenta.
export function MiPerfil() {
  const { usuario, token } = useSesion()
  const [cargado, setCargado] = useState(false)
  const [biografia, setBiografia] = useState('')
  const [enlace, setEnlace] = useState('')
  const [enlaceGuardado, setEnlaceGuardado] = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState(null)
  const [exito, setExito] = useState(false)
 
  useEffect(() => {
    let vigente = true
    obtenerPerfil(usuario.id)
      .then((perfil) => {
        if (!vigente) return
        setBiografia(perfil.biografia ?? '')
        setEnlace(perfil.enlace_personalizado ?? '')
        setEnlaceGuardado(perfil.enlace_personalizado)
        setCargado(true)
      })
      .catch(() => {})
    return () => {
      vigente = false
    }
  }, [usuario.id])
 
  async function guardar(evento) {
    evento.preventDefault()
    setError(null)
    setExito(false)
    setGuardando(true)
    try {
      // La API no permite borrar el alias: si el campo queda vacio, no se envia.
      const cambios = { biografia }
      if (enlace) cambios.enlace_personalizado = enlace
      const perfil = await guardarPerfil(token, cambios)
      setEnlace(perfil.enlace_personalizado ?? '')
      setEnlaceGuardado(perfil.enlace_personalizado)
      setExito(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setGuardando(false)
    }
  }
 
  if (!cargado) return null
 
  return (
    <Tarjeta className="mt-4 p-6">
      <h2 className="text-[17px]">Mi perfil</h2>
      <p className="mt-1 text-xs text-tinta/65">Así te ven quienes buscan ayuda.</p>
      <form onSubmit={guardar} className="mt-3 grid gap-3">
        <label className={claseEtiqueta}>
          Cómo te presentas
          <textarea
            value={biografia}
            onChange={(e) => setBiografia(e.target.value)}
            maxLength={LARGO_BIOGRAFIA}
            rows={4}
            className={claseCampo}
          />
        </label>
        <p className="text-xs text-tinta/65">
          {biografia.length} / {LARGO_BIOGRAFIA} caracteres
        </p>
        <label className={claseEtiqueta}>
          Enlace de tu perfil
          <input
            value={enlace}
            onChange={(e) => setEnlace(e.target.value.toLowerCase())}
            pattern="[a-z0-9_\-]{3,30}"
            title="De 3 a 30 caracteres: letras minúsculas, números, guiones y guiones bajos"
            maxLength={30}
            placeholder="por-ejemplo-rodrigo-salas"
            className={claseCampo}
          />
        </label>
        <p className="text-xs text-tinta/65">De 3 a 30 caracteres: letras minúsculas, números, guiones y guiones bajos.</p>
        {error && <Aviso tipo="error">{error}</Aviso>}
        {exito && <Aviso tipo="exito">Guardamos tu perfil.</Aviso>}
        <div className="flex flex-wrap gap-3">
          <Boton type="submit" tamano="chico" disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar perfil'}
          </Boton>
          <BotonEnlace to={`/u/${enlaceGuardado ?? usuario.id}`} tamano="chico" variante="secundario">
            Ver mi perfil público
          </BotonEnlace>
        </div>
      </form>
    </Tarjeta>
  )
}