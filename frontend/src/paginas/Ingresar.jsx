import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { useSesion } from '../sesion/useSesion'

function mensajePara(error) {
  if (error.estado === 401) return 'Correo o contraseña incorrectos.'
  if (error.estado === 403) return 'Tu cuenta está suspendida.'
  return error.message
}

export function Ingresar() {
  const { ingresar, usuario } = useSesion()
  const navegar = useNavigate()
  const ubicacion = useLocation()
  const destino = ubicacion.state?.desde ?? '/mi-cuenta'

  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  if (usuario) {
    return <Navigate to={destino} replace />
  }

  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await ingresar(correo.trim(), contrasena)
      navegar(destino, { replace: true })
    } catch (e) {
      setError(mensajePara(e))
      setEnviando(false)
    }
  }

  return (
    <section className="max-w-sm">
      <h1 className="text-3xl font-extrabold">Ingresar</h1>
      <form onSubmit={enviar} className="mt-6 grid gap-4" noValidate>
        <label className="grid gap-1">
          Correo
          <input
            type="email"
            autoComplete="email"
            required
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            className="rounded-md border border-grafito/30 px-3 py-2"
          />
        </label>
        <label className="grid gap-1">
          Contraseña
          <input
            type="password"
            autoComplete="current-password"
            required
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            className="rounded-md border border-grafito/30 px-3 py-2"
          />
        </label>
        {error && (
          <p role="alert" className="text-alerta">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={enviando}
          className="rounded-md bg-tinta px-5 py-3 font-bold text-papel hover:brightness-110 disabled:opacity-60"
        >
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </section>
  )
}
