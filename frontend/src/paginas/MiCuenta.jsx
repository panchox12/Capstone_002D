import { useSesion } from '../sesion/useSesion'
import { Avatar } from '../componentes/ui/Avatar'
import { Aviso } from '../componentes/ui/Aviso'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'

/** Pagina privada: solo se llega con sesion iniciada (ver RutaPrivada). */
export function MiCuenta() {
  const { usuario } = useSesion()

  return (
    <section className="max-w-2xl">
      <TituloPagina titulo={`Hola, ${usuario.nombre_visible}`} bajada="Los datos de tu cuenta." />

      {usuario.estado_cuenta === 'pendiente_confirmacion' && (
        <Aviso tipo="info" className="mb-4">
          Confirma tu correo para empezar a usar Cachai: abre el enlace que te enviamos al registrarte.
        </Aviso>
      )}

      <Tarjeta className="flex items-center gap-4 p-6">
        <Avatar nombre={usuario.nombre_visible} tamano="grande" />
        <dl className="grid gap-0.5">
          <dt className="text-xs text-tinta/65">Correo</dt>
          <dd className="font-semibold">{usuario.correo}</dd>
        </dl>
      </Tarjeta>
    </section>
  )
}
