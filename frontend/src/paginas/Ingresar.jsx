import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { claseCampo, claseEtiqueta } from '../componentes/ui/clases'

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
    <Tarjeta como="section" className="mx-auto mt-6 max-w-md p-7">
      <h1 className="text-[28px]">Ingresar</h1>
      <p className="mt-1 text-sm text-tinta/65">Con el correo y la contraseña de tu cuenta.</p>
      <form onSubmit={enviar} className="mt-6 grid gap-4" noValidate>
        <label className={claseEtiqueta}>
          Correo
          <input
            type="email"
            autoComplete="email"
            required
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            className={claseCampo}
          />
        </label>
        <label className={claseEtiqueta}>
          Contraseña
          <input
            type="password"
            autoComplete="current-password"
            required
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            className={claseCampo}
          />
        </label>
        {error && <Aviso tipo="error">{error}</Aviso>}
        <Boton type="submit" tamano="grande" disabled={enviando} className="mt-1 w-full">
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </Boton>
        <p className="text-center text-sm text-tinta/65">
          ¿Todavía no tienes cuenta?{' '}
          <Link to="/crear-cuenta" className="font-semibold text-oceano">
            Crea una
          </Link>
        </p>
      </form>
    </Tarjeta>
  )
}
