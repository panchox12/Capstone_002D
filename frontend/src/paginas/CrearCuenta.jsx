import { useState } from 'react'
import { Link, Navigate } from 'react-router'
import { registrar } from '../api/auth'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton, BotonEnlace } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { claseCampo, claseEtiqueta } from '../componentes/ui/clases'

/** Lo mismo que exige la API, revisado antes de enviar para avisar mientras se escribe. */
function faltasDeLaContrasena(contrasena) {
  const faltas = []
  if (contrasena.length < 10) faltas.push('al menos 10 caracteres')
  if (!/\d/.test(contrasena)) faltas.push('un número')
  if (!/\p{L}/u.test(contrasena)) faltas.push('una letra')
  return faltas
}

const VACIO = { nombre: '', correo: '', contrasena: '', terminos: false, grabacion: false }

export function CrearCuenta() {
  const { usuario } = useSesion()
  const [datos, setDatos] = useState(VACIO)
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [registrado, setRegistrado] = useState(null)

  if (usuario) {
    return <Navigate to="/mi-cuenta" replace />
  }

  function cambiar(campo) {
    return (evento) => {
      const { type, checked, value } = evento.target
      setDatos((anteriores) => ({ ...anteriores, [campo]: type === 'checkbox' ? checked : value }))
    }
  }

  const faltas = faltasDeLaContrasena(datos.contrasena)
  const completo =
    datos.nombre.trim().length >= 2 &&
    datos.correo.includes('@') &&
    faltas.length === 0 &&
    datos.terminos &&
    datos.grabacion

  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await registrar({
        nombre_visible: datos.nombre.trim(),
        correo: datos.correo.trim(),
        contrasena: datos.contrasena,
        acepta_terminos: datos.terminos,
        consentimiento_grabacion: datos.grabacion,
      })
      setRegistrado(datos.correo.trim())
    } catch (e) {
      setError(e.estado === 409 ? 'Ya existe una cuenta con ese correo.' : e.message)
    } finally {
      setEnviando(false)
    }
  }

  if (registrado) {
    return (
      <Tarjeta como="section" className="mx-auto mt-6 max-w-md p-7">
        <h1 className="text-[28px]">Revisa tu correo</h1>
        <p className="mt-2 text-sm text-tinta/65">
          Te enviamos un enlace a <strong className="text-tinta">{registrado}</strong>. Ábrelo para activar tu cuenta.
        </p>
        {import.meta.env.DEV && (
          <Aviso tipo="neutro" className="mt-4">
            Mientras desarrollamos, el enlace aparece en la terminal donde corre la API.
          </Aviso>
        )}
        <BotonEnlace to="/ingresar" variante="secundario" className="mt-6">
          Ir a ingresar
        </BotonEnlace>
      </Tarjeta>
    )
  }

  return (
    <Tarjeta como="section" className="mx-auto mt-6 max-w-lg p-7">
      <h1 className="text-[28px]">Crear cuenta</h1>
      <p className="mt-1 text-sm text-tinta/65">Con la misma cuenta pides ayuda y enseñas lo que sabes.</p>

      <form onSubmit={enviar} className="mt-6 grid gap-4" noValidate>
        <label className={claseEtiqueta}>
          Nombre visible
          <input autoComplete="name" value={datos.nombre} onChange={cambiar('nombre')} className={claseCampo} />
        </label>
        <label className={claseEtiqueta}>
          Correo
          <input
            type="email"
            autoComplete="email"
            value={datos.correo}
            onChange={cambiar('correo')}
            className={claseCampo}
          />
        </label>
        <div className="grid gap-1.5">
          <label className={claseEtiqueta}>
            Contraseña
            <input
              type="password"
              autoComplete="new-password"
              value={datos.contrasena}
              onChange={cambiar('contrasena')}
              aria-describedby="ayuda-contrasena"
              className={claseCampo}
            />
          </label>
          <p id="ayuda-contrasena" className="text-xs text-tinta/65">
            {faltas.length === 0 ? 'La contraseña cumple lo necesario.' : `Le falta: ${faltas.join(', ')}.`}
          </p>
        </div>

        <label className="flex items-start gap-3 text-sm">
          <input
            type="checkbox"
            checked={datos.terminos}
            onChange={cambiar('terminos')}
            className="mt-0.5 size-4 accent-oceano"
          />
          Acepto los términos y condiciones de Cachai
        </label>

        <div className="rounded-2xl bg-celeste p-4 text-abismo">
          <label className="flex items-start gap-3 text-sm font-semibold">
            <input
              type="checkbox"
              checked={datos.grabacion}
              onChange={cambiar('grabacion')}
              aria-describedby="detalle-grabacion"
              className="mt-0.5 size-4 accent-oceano"
            />
            Autorizo que mis sesiones se graben en audio y video
          </label>
          <p id="detalle-grabacion" className="mt-2 pl-7 text-xs leading-relaxed opacity-90">
            Todas las sesiones se graban para proteger a quienes usan Cachai. La grabación se borra a las 24 horas,
            salvo que alguien reporte la sesión. Solo el equipo de soporte puede verla, y únicamente para resolver un
            reporte. Nadie más puede verla ni descargarla, tampoco tú.
          </p>
        </div>

        {error && <Aviso tipo="error">{error}</Aviso>}
        <Boton type="submit" tamano="grande" disabled={!completo || enviando} className="mt-1 w-full">
          {enviando ? 'Creando tu cuenta…' : 'Crear cuenta'}
        </Boton>
        <p className="text-center text-sm text-tinta/65">
          ¿Ya tienes cuenta?{' '}
          <Link to="/ingresar" className="font-semibold text-oceano">
            Ingresa
          </Link>
        </p>
      </form>
    </Tarjeta>
  )
}
