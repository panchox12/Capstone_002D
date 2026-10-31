import { useState } from 'react'
import { useNavigate } from 'react-router'
import { buscarEspecialistas } from '../api/busqueda'
import { enviarSolicitud } from '../api/solicitudes'
import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { Avatar } from '../componentes/ui/Avatar'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { claseCampo, claseEtiqueta } from '../componentes/ui/clases'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { plural } from '../utilidades/formato'

const LARGO_MENSAJE = 280

function Reputacion({ resultado }) {
  if (resultado.reputacion_promedio === null) {
    return <span className="text-xs text-tinta/65">Usuario nuevo</span>
  }
  return (
    <span className="text-xs text-tinta/65">
      ★ {resultado.reputacion_promedio.toFixed(1).replace('.', ',')} ({resultado.total_evaluaciones})
    </span>
  )
}

function FormularioSolicitud({ resultado, dudaInicial, alEnviar }) {
  const [mensaje, setMensaje] = useState(dudaInicial.slice(0, LARGO_MENSAJE))
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)

  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await alEnviar(mensaje.trim())
    } catch (e) {
      setError(e.message)
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={enviar} className="mt-4 grid gap-3 border-t border-tinta/10 pt-4">
      <label className={claseEtiqueta}>
        Mensaje para {resultado.tutor_nombre}
        <textarea
          value={mensaje}
          onChange={(e) => setMensaje(e.target.value)}
          maxLength={LARGO_MENSAJE}
          rows={3}
          className={claseCampo}
        />
      </label>
      <p className="text-xs text-tinta/65">
        {resultado.en_linea
          ? `Está en línea: tiene 5 minutos para responder. Al enviar se retienen ${plural(resultado.precio_por_bloque, 'token', 'tokens')}.`
          : 'Está desconectado: tiene hasta 24 horas para responder. Tus tokens se retienen solo si acepta.'}
      </p>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <Boton type="submit" tamano="chico" disabled={enviando || !mensaje.trim()} className="justify-self-start">
        {enviando ? 'Enviando…' : 'Enviar solicitud'}
      </Boton>
    </form>
  )
}

function TarjetaResultado({ resultado, duda, alEnviar }) {
  const [abierta, setAbierta] = useState(false)

  return (
    <Tarjeta como="article" className="p-5">
      <div className="flex flex-wrap items-center gap-3">
        <Avatar nombre={resultado.tutor_nombre} />
        <div className="mr-auto">
          <h2 className="text-[15px]">{resultado.tutor_nombre}</h2>
          <Reputacion resultado={resultado} />
        </div>
        <Ficha variante={resultado.en_linea ? 'celeste' : 'gris'}>
          {resultado.en_linea ? 'En línea' : 'Desconectado'}
        </Ficha>
      </div>
      <p className="mt-3 text-sm font-semibold">{resultado.tema_nombre}</p>
      <p className="text-xs text-tinta/65">{resultado.ruta}</p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <p className="mr-auto text-sm">
          <span className="font-extrabold">{plural(resultado.precio_por_bloque, 'token', 'tokens')}</span> por bloque de
          15 minutos
        </p>
        {!abierta && (
          <Boton tamano="chico" onClick={() => setAbierta(true)} aria-label={`Pedir ayuda a ${resultado.tutor_nombre}`}>
            Pedir ayuda
          </Boton>
        )}
      </div>
      {abierta && (
        <FormularioSolicitud
          resultado={resultado}
          dudaInicial={duda}
          alEnviar={(mensaje) => alEnviar(resultado, mensaje)}
        />
      )}
    </Tarjeta>
  )
}

export function Buscar() {
  const { token } = useSesion()
  const { actualizar } = useSaldo()
  const navegar = useNavigate()
  const [duda, setDuda] = useState('')
  const [soloEnLinea, setSoloEnLinea] = useState(false)
  const [resultados, setResultados] = useState(null)
  const [buscada, setBuscada] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)

  async function buscar(evento) {
    evento.preventDefault()
    setError(null)
    setCargando(true)
    try {
      const respuesta = await buscarEspecialistas(token, { duda: duda.trim(), soloEnLinea })
      setResultados(respuesta.resultados)
      setBuscada(duda.trim())
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }

  async function pedirAyuda(resultado, mensaje) {
    const solicitud = await enviarSolicitud(token, resultado.habilidad_id, mensaje)
    actualizar()
    const aviso =
      solicitud.modalidad === 'en_vivo'
        ? `Le enviaste tu duda a ${resultado.tutor_nombre}. Tiene 5 minutos para responder.`
        : `Le enviaste tu duda a ${resultado.tutor_nombre}. Te avisamos cuando responda.`
    navegar('/solicitudes', { state: { aviso } })
  }

  return (
    <section className="max-w-3xl">
      <TituloPagina
        titulo="¿Qué duda tienes?"
        bajada="Escríbela con tus palabras, como se la contarías a un amigo. No necesitas saber cómo se llama el tema."
      />

      <form onSubmit={buscar} className="grid gap-3">
        <label className={claseEtiqueta}>
          Tu duda
          <input
            value={duda}
            onChange={(e) => setDuda(e.target.value)}
            placeholder="Por ejemplo: se me corta la luz cuando prendo el hervidor"
            maxLength={200}
            className={claseCampo}
          />
        </label>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={soloEnLinea}
              onChange={(e) => setSoloEnLinea(e.target.checked)}
              className="size-4 accent-oceano"
            />
            Solo personas en línea
          </label>
          <Boton type="submit" disabled={cargando || duda.trim().length < 3} className="ml-auto">
            {cargando ? 'Buscando…' : 'Buscar'}
          </Boton>
        </div>
      </form>

      {error && (
        <Aviso tipo="error" className="mt-4">
          {error}
        </Aviso>
      )}

      {resultados && resultados.length === 0 && (
        <Aviso tipo="neutro" className="mt-6">
          No encontramos a nadie para esa duda. Prueba contándola de otra forma.
        </Aviso>
      )}

      {resultados && resultados.length > 0 && (
        <div className="mt-6 grid gap-3.5">
          {resultados.map((resultado) => (
            <TarjetaResultado
              key={resultado.habilidad_id}
              resultado={resultado}
              duda={buscada}
              alEnviar={pedirAyuda}
            />
          ))}
        </div>
      )}
    </section>
  )
}