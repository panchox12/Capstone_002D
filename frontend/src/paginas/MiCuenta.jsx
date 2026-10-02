import { useSesion } from '../sesion/useSesion'

/** Pagina privada: solo se llega con sesion iniciada (ver RutaPrivada). */
export function MiCuenta() {
  const { usuario } = useSesion()

  return (
    <section>
      <h1 className="text-3xl font-extrabold">Hola, {usuario.nombre_visible}</h1>
      <dl className="mt-6 grid gap-1">
        <dt className="font-bold">Correo</dt>
        <dd>{usuario.correo}</dd>
      </dl>
      {usuario.estado_cuenta === 'pendiente_confirmacion' && (
        <p role="status" className="mt-6 rounded-md bg-resaltador/40 px-4 py-3">
          Confirma tu correo para empezar a usar Cachai: abre el enlace que te enviamos al registrarte.
        </p>
      )}
    </section>
  )
}
