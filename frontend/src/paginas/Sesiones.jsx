import { useEffect, useState } from 'react'
import { obtenerSesiones } from '../api/sesiones'
import { Aviso } from '../componentes/ui/Aviso'
import { BotonEnlace } from '../componentes/ui/Boton'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { ESTADOS_SESION } from '../sala/tiempo'
import { useSesion } from '../sesion/useSesion'
import { fechaCorta, plural } from '../utilidades/formato'

/** Historial: las sesiones donde ayudaste o te ayudaron, la mas nueva primero. */
export function Sesiones() {
  const { token, usuario } = useSesion()
  const [sesiones, setSesiones] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let vigente = true
    obtenerSesiones(token)
      .then((lista) => {
        if (vigente) setSesiones(lista)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [token])

  if (error) return <Aviso tipo="error">{error}</Aviso>
  if (sesiones === null) {
    return (
      <p role="status" className="text-sm text-tinta/65">
        Cargando tus sesiones…
      </p>
    )
  }

  return (
    <section className="max-w-3xl">
      <TituloPagina titulo="Sesiones" bajada="Tus videollamadas: las que vienen y las que ya pasaron." />
      {sesiones.length === 0 ? (
        <p className="text-sm text-tinta/65">Todavía no tienes sesiones. Aparecen aquí cuando aceptan una solicitud.</p>
      ) : (
        <div className="grid gap-3">
          {sesiones.map((sesion) => {
            const soyTutor = sesion.tutor.id === usuario?.id
            const otra = soyTutor ? sesion.aprendiz : sesion.tutor
            const estado = ESTADOS_SESION[sesion.estado]
            return (
              <Tarjeta key={sesion.id} como="article" className="flex flex-wrap items-center gap-3 p-5">
                <div className="mr-auto">
                  <h3 className="text-[15px]">
                    {sesion.tema_nombre} · {soyTutor ? 'ayudaste a' : 'con'} {otra.nombre_visible}
                  </h3>
                  <p className="mt-1 text-xs text-tinta/65">
                    {fechaCorta(sesion.fecha_apertura_sala)} · {plural(sesion.bloques_cobrados, 'bloque', 'bloques')}
                  </p>
                </div>
                <Ficha variante={estado.variante}>{estado.texto}</Ficha>
                <BotonEnlace to={`/sesiones/${sesion.id}`} tamano="chico" variante="secundario">
                  Abrir
                </BotonEnlace>
              </Tarjeta>
            )
          })}
        </div>
      )}
    </section>
  )
}