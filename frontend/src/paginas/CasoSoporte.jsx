import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { abrirGrabacion, obtenerAccesos, obtenerReporte, resolverReporte } from '../api/soporte'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton, BotonEnlace } from '../componentes/ui/Boton'
import { claseCampo, claseEtiqueta } from '../componentes/ui/clases'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { useSesion } from '../sesion/useSesion'
import { ESTADOS_REPORTE, MOTIVOS_REPORTE } from '../soporte/textos'
import { fechaCorta, plural } from '../utilidades/formato'
 
const GRABACION = {
  grabando: 'Todavía se está procesando',
  disponible: 'Disponible',
  fallida: 'No se pudo grabar',
  borrada: 'Ya se borró',
}
 
function Dato({ titulo, children }) {
  return (
    <div>
      <dt className="text-xs text-tinta/65">{titulo}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}
 
function FormularioResolucion({ reporte, alResolver }) {
  const [fundado, setFundado] = useState(null)
  const [resolucion, setResolucion] = useState('')
  const [sancion, setSancion] = useState('')
  const [dias, setDias] = useState('7')
  const [enviando, setEnviando] = useState(false)
 
  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    await alResolver({
      fundado,
      resolucion,
      tipo_sancion: fundado && sancion ? sancion : null,
      dias_suspension: fundado && sancion === 'temporal' ? Number(dias) : null,
    })
    setEnviando(false)
  }
 
  const listo = fundado !== null && resolucion.trim().length >= 10
 
  return (
    <form onSubmit={enviar} className="grid gap-3">
      <fieldset className="flex gap-4 text-sm">
        <legend className="mb-1 text-[13px] font-semibold">Decisión</legend>
        <label className="flex items-center gap-2">
          <input type="radio" name="fundado" checked={fundado === true} onChange={() => setFundado(true)} />
          Fundado
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" name="fundado" checked={fundado === false} onChange={() => setFundado(false)} />
          Desestimado
        </label>
      </fieldset>
      <label className={claseEtiqueta}>
        Justificación
        <textarea className={claseCampo} rows={3} value={resolucion} onChange={(e) => setResolucion(e.target.value)} />
      </label>
      {fundado && (
        <div className="flex flex-wrap gap-3">
          <label className={claseEtiqueta}>
            Sanción a {reporte.reportado.nombre_visible}
            <select className={claseCampo} value={sancion} onChange={(e) => setSancion(e.target.value)}>
              <option value="">Sin sanción</option>
              <option value="temporal">Suspensión temporal</option>
              <option value="definitiva">Suspensión definitiva</option>
            </select>
          </label>
          {sancion === 'temporal' && (
            <label className={claseEtiqueta}>
              Días
              <input
                type="number"
                min="1"
                max="365"
                className={`${claseCampo} w-24`}
                value={dias}
                onChange={(e) => setDias(e.target.value)}
              />
            </label>
          )}
        </div>
      )}
      <Boton type="submit" className="justify-self-start" disabled={!listo || enviando}>
        Resolver reporte
      </Boton>
    </form>
  )
}
 
/** Un reporte: los datos de la sesion, la grabacion, la bitacora y la resolucion. */
export function CasoSoporte() {
  const { reporteId } = useParams()
  const { token } = useSesion()
  const [reporte, setReporte] = useState(null)
  const [accesos, setAccesos] = useState([])
  const [mensaje, setMensaje] = useState(null)
 
  const cargar = useCallback(
    () =>
      Promise.all([obtenerReporte(token, reporteId), obtenerAccesos(token, reporteId)]).then(([datos, bitacora]) => {
        setReporte(datos)
        setAccesos(bitacora)
      }),
    [token, reporteId],
  )
 
  useEffect(() => {
    cargar().catch((e) => setMensaje({ tipo: 'error', texto: e.message }))
  }, [cargar])
 
  async function verGrabacion() {
    setMensaje(null)
    try {
      const { url } = await abrirGrabacion(token, reporteId)
      window.open(url, '_blank', 'noopener')
      setAccesos(await obtenerAccesos(token, reporteId))
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e.message })
    }
  }
 
  async function resolver(datos) {
    setMensaje(null)
    try {
      setReporte(await resolverReporte(token, reporteId, datos))
      setMensaje({ tipo: 'exito', texto: 'Reporte resuelto. Se avisó a quien reportó.' })
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e.message })
    }
  }
 
  if (reporte === null) {
    return mensaje ? <Aviso tipo="error">{mensaje.texto}</Aviso> : null
  }
 
  const estado = ESTADOS_REPORTE[reporte.estado]
  const abierto = reporte.estado === 'abierto'
 
  return (
    <section className="max-w-3xl">
      <TituloPagina titulo={`Folio ${reporte.folio}`} bajada={MOTIVOS_REPORTE[reporte.motivo]}>
        <div className="mt-3 flex gap-2">
          <Ficha variante={estado.variante}>{estado.texto}</Ficha>
          {reporte.congela_pago && abierto && <Ficha variante="contorno">Pago congelado</Ficha>}
        </div>
      </TituloPagina>
      {mensaje && (
        <Aviso tipo={mensaje.tipo} className="mb-4">
          {mensaje.texto}
        </Aviso>
      )}
 
      <Tarjeta className="mb-4 p-6">
        <p className="text-sm">“{reporte.descripcion}”</p>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          <Dato titulo="Reporta">{reporte.reportante.nombre_visible}</Dato>
          <Dato titulo="Reportado">
            {reporte.reportado.nombre_visible} · {plural(reporte.sanciones_previas_reportado, 'sanción previa', 'sanciones previas')}
          </Dato>
          <Dato titulo="Sesión">
            {reporte.tema_nombre} · {plural(reporte.bloques_cobrados, 'bloque', 'bloques')} de {reporte.precio_bloque} tokens
          </Dato>
          <Dato titulo="Cierre">
            {reporte.fecha_cierre ? fechaCorta(reporte.fecha_cierre) : 'Sin cierre'} · {reporte.motivo_cierre ?? '—'}
          </Dato>
          <Dato titulo="Tokens">
            Retenidos {reporte.pago.retenido} · pagados {reporte.pago.pagado} · devueltos {reporte.pago.devuelto}
          </Dato>
          <Dato titulo="Grabación">{reporte.grabacion ? GRABACION[reporte.grabacion] : 'No se grabó'}</Dato>
        </dl>
        {abierto && reporte.grabacion === 'disponible' && (
          <Boton tamano="chico" variante="secundario" className="mt-4" onClick={verGrabacion}>
            Ver grabación
          </Boton>
        )}
        {accesos.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold">Quién vio la grabación</p>
            <ul className="mt-1 text-xs text-tinta/75">
              {accesos.map((acceso) => (
                <li key={acceso.fecha}>
                  {acceso.soporte} · {new Date(acceso.fecha).toLocaleString('es-CL')}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Tarjeta>
 
      <Tarjeta className="p-6">
        <h2 className="mb-3 text-base">Resolución</h2>
        {abierto ? (
          <FormularioResolucion reporte={reporte} alResolver={resolver} />
        ) : (
          <p className="text-sm">{reporte.resolucion}</p>
        )}
      </Tarjeta>
 
      <BotonEnlace to="/soporte" variante="secundario" tamano="chico" className="mt-4">
        Volver a la bandeja
      </BotonEnlace>
    </section>
  )
}