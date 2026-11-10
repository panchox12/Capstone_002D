import { useState } from 'react'
import { plural } from '../utilidades/formato'
import { Aviso } from './ui/Aviso'
import { Boton } from './ui/Boton'
import { claseCampo, claseEtiqueta } from './ui/clases'
 
const LARGO_MENSAJE = 280
 
// Mensaje para pedir ayuda. Lo usan el buscador y el perfil publico.
export function FormularioSolicitud({ tutorNombre, enLinea, precio, dudaInicial = '', alEnviar }) {
  const [mensaje, setMensaje] = useState(dudaInicial.slice(0, LARGO_MENSAJE))
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
 
  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await alEnviar(mensaje.trim())
    } catch (e) {
      setError(e.message)
      setEnviando(false)
    }
  }
 
  return (
    <form onSubmit={enviar} className="mt-4 grid gap-3 border-t border-tinta/10 pt-4">
      <label className={claseEtiqueta}>
        Mensaje para {tutorNombre}
        <textarea
          value={mensaje}
          onChange={(e) => setMensaje(e.target.value)}
          maxLength={LARGO_MENSAJE}
          rows={3}
          className={claseCampo}
        />
      </label>
      <p className="text-xs text-tinta/65">
        {enLinea
          ? `Está en línea: tiene 5 minutos para responder. Al enviar se retienen ${plural(precio, 'token', 'tokens')}.`
          : 'Está desconectado: tiene hasta 24 horas para responder. Tus tokens se retienen solo si acepta.'}
      </p>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <Boton type="submit" tamano="chico" disabled={enviando || !mensaje.trim()} className="justify-self-start">
        {enviando ? 'Enviando…' : 'Enviar solicitud'}
      </Boton>
    </form>
  )
}