import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { confirmarCorreo } from '../api/auth'
import { useSesion } from '../sesion/useSesion'
import { BotonEnlace } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'

/** La pagina que abre el enlace del correo. Le pasa el token a la API y muestra el resultado. */
export function ConfirmarCorreo() {
  const { token } = useParams()
  const { usuario, refrescar } = useSesion()
  const [resultado, setResultado] = useState({ estado: 'confirmando' })

  useEffect(() => {
    let vigente = true
    confirmarCorreo(token)
      .then(() => {
        if (vigente) setResultado({ estado: 'listo' })
      })
      .catch((e) => {
        if (vigente) setResultado({ estado: 'error', mensaje: e.message })
      })
    return () => {
      vigente = false
    }
  }, [token])

  // Si ya habia sesion iniciada, sus datos todavia dicen "pendiente de confirmacion"
  useEffect(() => {
    if (resultado.estado === 'listo') refrescar().catch(() => {})
  }, [resultado.estado, refrescar])

  if (resultado.estado === 'confirmando') {
    return (
      <p role="status" className="text-sm text-tinta/65">
        Confirmando tu correo…
      </p>
    )
  }

  if (resultado.estado === 'error') {
    return (
      <Tarjeta como="section" className="mx-auto mt-6 max-w-md p-7">
        <h1 className="text-[28px]">No pudimos confirmar tu correo</h1>
        <p role="alert" className="mt-2 text-sm text-alerta">
          {resultado.mensaje}
        </p>
        <BotonEnlace to="/" variante="secundario" className="mt-6">
          Volver al inicio
        </BotonEnlace>
      </Tarjeta>
    )
  }

  return (
    <Tarjeta como="section" className="mx-auto mt-6 max-w-md p-7">
      <h1 className="text-[28px]">Tu cuenta está activa</h1>
      <p className="mt-2 text-sm text-tinta/65">
        Ya puedes usar Cachai. El siguiente paso es verificar tu identidad, para poder pedir y ofrecer consultas.
      </p>
      <BotonEnlace to={usuario ? '/verificar' : '/ingresar'} className="mt-6">
        {usuario ? 'Verificar mi identidad' : 'Ingresar'}
      </BotonEnlace>
    </Tarjeta>
  )
}
