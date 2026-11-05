import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { entrarASala, obtenerSesion } from '../api/sesiones'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton, BotonEnlace } from '../componentes/ui/Boton'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { BotonBloquear } from '../sala/BotonBloquear'
import { ESTADOS_SESION, reloj } from '../sala/tiempo'
import { Valorar } from '../sala/Valorar'
import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { plural } from '../utilidades/formato'

// LiveKit pesa: se descarga recien cuando alguien entra a una sala.
const VideoLlamada = lazy(() => import('../sala/VideoLlamada').then((m) => ({ default: m.VideoLlamada })))

// Mientras la sesion esta viva se pregunta seguido: el tiempo lo lleva el servidor.
const MILISEGUNDOS_ENTRE_REVISIONES = 5000

const AVISO_GRABACION =
  'Esta sesión se graba. La grabación se borra a las 24 horas, salvo que alguien la reporte, y solo la ve el equipo de soporte.'

function viva(sesion) {
  return sesion.estado === 'esperando' || sesion.estado === 'en_curso'
}

function Reloj({ sesion, segundosPasados }) {
  if (sesion.estado === 'esperando') {
    return (
      <p className="text-sm">
        Tienen <span className="font-reloj font-semibold">{reloj(sesion.segundos_para_conectarse - segundosPasados)}</span>{' '}
        para conectarse. El cobro empieza cuando estén los dos.
      </p>
    )
  }
  // Con alguien caido el servidor congela el tiempo: aca tampoco se descuenta.
  const restantes = sesion.pausa_activa ? sesion.segundos_restantes_bloque : sesion.segundos_restantes_bloque - segundosPasados
  return (
    <p className="text-sm">
      Quedan <span className="font-reloj font-semibold">{reloj(restantes)}</span> pagados ·{' '}
      {plural(sesion.bloques_cobrados, 'bloque', 'bloques')}
    </p>
  )
}

function AvisoPausa({ sesion, segundosPasados, usuarioId }) {
  if (!sesion.pausa_activa) return null
  const soyYo = sesion.usuario_caido_id === usuarioId
  const quien = soyYo
    ? 'Perdiste la conexión'
    : `${[sesion.aprendiz, sesion.tutor].find((p) => p.id === sesion.usuario_caido_id)?.nombre_visible ?? 'La otra persona'} perdió la conexión`
  return (
    <Aviso tipo="info" className="mt-4">
      {quien}. Tiene {reloj(sesion.segundos_para_reconectar - segundosPasados)} para volver; mientras tanto el reloj está
      detenido. Pausas usadas: {sesion.pausas_usadas} de {sesion.pausas_maximas}.
    </Aviso>
  )
}

/** La sala de una sesion: estado, tiempo y la videollamada. */
export function Sala() {
  const { sesionId } = useParams()
  const { token, usuario } = useSesion()
  const { actualizar } = useSaldo()
  const [sesion, setSesion] = useState(null)
  const [permiso, setPermiso] = useState(null)
  const [error, setError] = useState(null)
  const [entrando, setEntrando] = useState(false)
  const [segundosPasados, setSegundosPasados] = useState(0)

  const cargar = useCallback(
    () =>
      obtenerSesion(token, sesionId).then((datos) => {
        setSesion(datos)
        setSegundosPasados(0)
        return datos
      }),
    [token, sesionId],
  )

  // Al entrar y cada 5 segundos mientras la sesion siga viva.
  useEffect(() => {
    let vigente = true
    let revision
    const revisar = () =>
      cargar()
        .then((datos) => {
          if (vigente && !viva(datos)) {
            clearInterval(revision)
            setPermiso(null)
            actualizar()
          }
        })
        .catch((e) => {
          if (vigente) setError(e.message)
        })
    revisar()
    revision = setInterval(revisar, MILISEGUNDOS_ENTRE_REVISIONES)
    return () => {
      vigente = false
      clearInterval(revision)
    }
  }, [cargar, actualizar])

  useEffect(() => {
    const segundero = setInterval(() => setSegundosPasados((s) => s + 1), 1000)
    return () => clearInterval(segundero)
  }, [])

  async function entrar() {
    setError(null)
    setEntrando(true)
    try {
      setPermiso(await entrarASala(token, sesionId))
    } catch (e) {
      setError(e.message)
    } finally {
      setEntrando(false)
    }
  }

  if (sesion === null) {
    return error ? (
      <Aviso tipo="error">{error}</Aviso>
    ) : (
      <p role="status" className="text-sm text-tinta/65">
        Cargando la sesión…
      </p>
    )
  }

  const soyTutor = sesion.tutor.id === usuario?.id
  const otra = soyTutor ? sesion.aprendiz : sesion.tutor
  const estado = ESTADOS_SESION[sesion.estado]

  return (
    <section>
      <TituloPagina titulo={sesion.tema_nombre} bajada={`${soyTutor ? 'Ayudas a' : 'Te ayuda'} ${otra.nombre_visible}`}>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Ficha variante={estado.variante}>{estado.texto}</Ficha>
          {sesion.estado === 'en_curso' && <Ficha variante="contorno">● Grabando</Ficha>}
        </div>
      </TituloPagina>

      {error && (
        <Aviso tipo="error" className="mb-4">
          {error}
        </Aviso>
      )}

      {viva(sesion) && (
        <Tarjeta className="mb-4">
          <Reloj sesion={sesion} segundosPasados={segundosPasados} />
          <AvisoPausa sesion={sesion} segundosPasados={segundosPasados} usuarioId={usuario?.id} />
          {!permiso && (
            <>
              <p className="mt-3 text-xs text-tinta/65">{AVISO_GRABACION}</p>
              <Boton className="mt-4" onClick={entrar} disabled={entrando}>
                {entrando ? 'Conectando…' : 'Entrar a la sala'}
              </Boton>
            </>
          )}
        </Tarjeta>
      )}

      {permiso && viva(sesion) && (
        <Suspense fallback={<p role="status" className="text-sm text-tinta/65">Abriendo la videollamada…</p>}>
          <VideoLlamada permiso={permiso} alSalir={() => setPermiso(null)} />
        </Suspense>
      )}

      {!viva(sesion) && (
        <Tarjeta className="max-w-2xl">
          <h2 className="text-base">Resumen</h2>
          <p className="mt-2 text-sm">
            {sesion.motivo_cierre ? `Motivo de cierre: ${sesion.motivo_cierre}.` : 'La sesión terminó.'}
          </p>
          <p className="mt-1 text-sm">
            {plural(sesion.bloques_cobrados, 'bloque cobrado', 'bloques cobrados')} ·{' '}
            {plural(sesion.bloques_cobrados * sesion.precio_bloque, 'token', 'tokens')}
          </p>
          {sesion.estado === 'terminada' && sesion.fecha_conexion_ambos && (
            <Valorar sesionId={sesion.id} nombre={otra.nombre_visible} />
          )}
          <BotonBloquear usuarioId={otra.id} nombre={otra.nombre_visible} />
          <div>
            <BotonEnlace to="/sesiones" variante="secundario" tamano="chico" className="mt-4">
              Volver a mis sesiones
            </BotonEnlace>
          </div>
        </Tarjeta>
      )}
    </section>
  )
}