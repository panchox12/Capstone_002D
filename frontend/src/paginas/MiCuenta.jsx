import { useEffect, useState } from 'react'
import { obtenerEstadoVerificacion } from '../api/verificacion'
import { useSesion } from '../sesion/useSesion'
import { Avatar } from '../componentes/ui/Avatar'
import { Aviso } from '../componentes/ui/Aviso'
import { BotonEnlace } from '../componentes/ui/Boton'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'

/** Pagina privada: solo se llega con sesion iniciada (ver RutaPrivada). */
export function MiCuenta() {
  const { usuario, token } = useSesion()
  const [verificacion, setVerificacion] = useState(null)
  const activa = usuario.estado_cuenta === 'activa'

  // Una cuenta sin confirmar todavia no puede consultar su verificacion
  useEffect(() => {
    if (!activa) return undefined
    let vigente = true
    obtenerEstadoVerificacion(token)
      .then((datos) => {
        if (vigente) setVerificacion(datos)
      })
      .catch(() => {})
    return () => {
      vigente = false
    }
  }, [activa, token])

  return (
    <section className="max-w-2xl">
      <TituloPagina titulo={`Hola, ${usuario.nombre_visible}`} bajada="Los datos de tu cuenta." />

      {usuario.estado_cuenta === 'pendiente_confirmacion' && (
        <Aviso tipo="info" className="mb-4">
          Confirma tu correo para empezar a usar Cachai: abre el enlace que te enviamos al registrarte.
        </Aviso>
      )}

      <Tarjeta className="flex flex-wrap items-center gap-4 p-6">
        <Avatar nombre={usuario.nombre_visible} tamano="grande" />
        <dl className="mr-auto grid gap-0.5">
          <dt className="text-xs text-tinta/65">Correo</dt>
          <dd className="font-semibold">{usuario.correo}</dd>
        </dl>
        {verificacion?.verificado && <Ficha>Identidad verificada</Ficha>}
      </Tarjeta>

      {verificacion && !verificacion.verificado && (
        <Tarjeta variante="oceano" className="mt-4 p-6">
          <h2 className="text-[17px] text-white">Verifica tu identidad</h2>
          <p className="mt-1 mb-4 text-[13px] opacity-90">
            Es el último paso para pedir ayuda y para enseñar lo que sabes. Toma menos de un minuto.
          </p>
          <BotonEnlace to="/verificar" variante="invertido" tamano="chico">
            Verificar ahora
          </BotonEnlace>
        </Tarjeta>
      )}
    </section>
  )
}
