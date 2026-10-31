import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router'
import { obtenerEnviadas, obtenerRecibidas, responderSolicitud } from '../api/solicitudes'
import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { plural } from '../utilidades/formato'
 
// Cada cuanto se vuelven a pedir las solicitudes para ver respuestas nuevas.
const MILISEGUNDOS_ENTRE_REVISIONES = 15_000
 
const ESTADOS = {
  pendiente: { texto: 'Pendiente', variante: 'celeste' },
  aceptada: { texto: 'Aceptada', variante: 'celeste' },
  rechazada: { texto: 'Rechazada', variante: 'gris' },
  vencida: { texto: 'Sin respuesta', variante: 'gris' },
  cancelada: { texto: 'Cancelada', variante: 'gris' },
}
 
// 290 segundos -> "4:50"; 3 horas o mas -> "3 h 5 min".
function tiempoRestante(segundos) {
  if (segundos >= 3600) {
    return `${Math.floor(segundos / 3600)} h ${Math.floor((segundos % 3600) / 60)} min`
  }
  return `${Math.floor(segundos / 60)}:${String(segundos % 60).padStart(2, '0')}`
}
 
function TarjetaSolicitud({ solicitud, rol, segundosPasados, alResponder, ocupada }) {
  const otra = rol === 'tutor' ? solicitud.aprendiz : solicitud.tutor
  const estado = ESTADOS[solicitud.estado]
  const pendiente = solicitud.estado === 'pendiente'
  const restantes = Math.max(0, solicitud.segundos_restantes - segundosPasados)
 
  return (
    <Tarjeta como="article" className="p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="mr-auto text-[15px]">
          {solicitud.tema_nombre} · {rol === 'tutor' ? 'de' : 'para'} {otra.nombre_visible}
        </h3>
        <Ficha variante="contorno">{solicitud.modalidad === 'en_vivo' ? 'En vivo' : 'Diferida'}</Ficha>
        <Ficha variante={estado.variante}>{estado.texto}</Ficha>
      </div>
      <p className="mt-2 text-sm">“{solicitud.mensaje}”</p>
      <p className="mt-2 text-xs text-tinta/65">
        {plural(solicitud.precio_bloque, 'token', 'tokens')} por bloque
        {pendiente && ` · quedan ${tiempoRestante(restantes)} para responder`}
      </p>
 
      {pendiente && rol === 'tutor' && (
        <div className="mt-4 flex gap-2">
          <Boton tamano="chico" disabled={ocupada} onClick={() => alResponder(solicitud, 'aceptar')}>
            Aceptar
          </Boton>
          <Boton
            tamano="chico"
            variante="secundario"
            disabled={ocupada}
            onClick={() => alResponder(solicitud, 'rechazar')}
          >
            Rechazar
          </Boton>
        </div>
      )}
      {pendiente && rol === 'aprendiz' && (
        <Boton
          tamano="chico"
          variante="secundario"
          className="mt-4"
          disabled={ocupada}
          onClick={() => alResponder(solicitud, 'cancelar')}
        >
          Cancelar solicitud
        </Boton>
      )}
    </Tarjeta>
  )
}
 
const MENSAJES = {
  aceptar: 'Aceptaste. La sala ya está abierta: tienen 5 minutos para conectarse.',
  rechazar: 'Rechazaste la solicitud. Los tokens volvieron a quien te escribió.',
  cancelar: 'Cancelaste la solicitud. Tus tokens retenidos ya volvieron.',
}
 
export function Solicitudes() {
  const { token } = useSesion()
  const { actualizar } = useSaldo()
  const ubicacion = useLocation()
  const [recibidas, setRecibidas] = useState(null)
  const [enviadas, setEnviadas] = useState(null)
  const [segundosPasados, setSegundosPasados] = useState(0)
  const [ocupada, setOcupada] = useState(null)
  const [mensaje, setMensaje] = useState(
    ubicacion.state?.aviso ? { tipo: 'exito', texto: ubicacion.state.aviso } : null,
  )
 
  const cargar = useCallback(
    () =>
      Promise.all([obtenerRecibidas(token), obtenerEnviadas(token)]).then(([nuevasRecibidas, nuevasEnviadas]) => {
        setRecibidas(nuevasRecibidas)
        setEnviadas(nuevasEnviadas)
        setSegundosPasados(0)
      }),
    [token],
  )
 
  // Al entrar y cada 15 segundos, para ver las respuestas nuevas.
  useEffect(() => {
    let vigente = true
    const revisar = () =>
      cargar().catch((e) => {
        if (vigente) setMensaje({ tipo: 'error', texto: e.message })
      })
    revisar()
    const revision = setInterval(revisar, MILISEGUNDOS_ENTRE_REVISIONES)
    return () => {
      vigente = false
      clearInterval(revision)
    }
  }, [cargar])
 
  // El tiempo lo calcula el servidor; aca solo se descuenta entre una revision y otra.
  useEffect(() => {
    const reloj = setInterval(() => setSegundosPasados((s) => s + 1), 1000)
    return () => clearInterval(reloj)
  }, [])
 
  async function responder(solicitud, accion) {
    setMensaje(null)
    setOcupada(solicitud.id)
    try {
      await responderSolicitud(token, solicitud.id, accion)
      setMensaje({ tipo: 'exito', texto: MENSAJES[accion] })
      await Promise.all([cargar(), actualizar()])
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e.message })
    } finally {
      setOcupada(null)
    }
  }
 
  if (recibidas === null || enviadas === null) {
    return (
      <>
        {mensaje && <Aviso tipo={mensaje.tipo}>{mensaje.texto}</Aviso>}
        <p role="status" className="mt-3 text-sm text-tinta/65">
          Cargando tus solicitudes…
        </p>
      </>
    )
  }
 
  const secciones = [
    { titulo: 'Recibidas', rol: 'tutor', lista: recibidas, vacia: 'Nadie te ha escrito todavía.' },
    { titulo: 'Enviadas', rol: 'aprendiz', lista: enviadas, vacia: 'No has enviado solicitudes.' },
  ]
 
  return (
    <section className="max-w-3xl">
      <TituloPagina titulo="Solicitudes" bajada="Las dudas que te enviaron y las que enviaste." />
      {mensaje && (
        <Aviso tipo={mensaje.tipo} className="mb-5">
          {mensaje.texto}
        </Aviso>
      )}
      {secciones.map((seccion) => (
        <div key={seccion.rol} className="mb-8">
          <h2 className="mb-3 text-base">{seccion.titulo}</h2>
          {seccion.lista.length === 0 ? (
            <p className="text-sm text-tinta/65">{seccion.vacia}</p>
          ) : (
            <div className="grid gap-3">
              {seccion.lista.map((solicitud) => (
                <TarjetaSolicitud
                  key={solicitud.id}
                  solicitud={solicitud}
                  rol={seccion.rol}
                  segundosPasados={segundosPasados}
                  alResponder={responder}
                  ocupada={ocupada === solicitud.id}
                />
              ))}
            </div>
          )}
        </div>
      ))}
    </section>
  )
}