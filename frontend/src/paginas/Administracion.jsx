import { useEffect, useState } from 'react'
import { cambiarParametro, obtenerIndicadores, obtenerParametros } from '../api/administracion'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { claseCampo } from '../componentes/ui/clases'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { useSesion } from '../sesion/useSesion'
 
const PORCENTAJE = new Intl.NumberFormat('es-CL', { style: 'percent', maximumFractionDigits: 1 })
 
function porcentaje(valor) {
  return PORCENTAJE.format(valor)
}
 
function Indicador({ titulo, valor, ayuda }) {
  return (
    <Tarjeta className="p-5">
      <p className="text-xs text-tinta/65">{titulo}</p>
      <p className="mt-1 font-reloj text-2xl font-semibold">{valor}</p>
      {ayuda && <p className="mt-1 text-xs text-tinta/65">{ayuda}</p>}
    </Tarjeta>
  )
}
 
function FilaParametro({ parametro, alGuardar }) {
  const [valor, setValor] = useState(parametro.valor)
  const [guardando, setGuardando] = useState(false)
  const cambiado = valor !== parametro.valor
 
  async function guardar(evento) {
    evento.preventDefault()
    setGuardando(true)
    await alGuardar(parametro.nombre, Number(valor))
    setGuardando(false)
  }
 
  return (
    <form onSubmit={guardar} className="flex flex-wrap items-center gap-3 py-2">
      <label htmlFor={`param-${parametro.nombre}`} className="mr-auto min-w-60 text-sm">
        {parametro.descripcion ?? parametro.nombre}
        <span className="block font-reloj text-xs text-tinta/65">{parametro.nombre}</span>
      </label>
      <input
        id={`param-${parametro.nombre}`}
        type="number"
        min="0"
        className={`${claseCampo} w-28`}
        value={valor}
        onChange={(e) => setValor(e.target.value)}
      />
      <Boton type="submit" tamano="chico" disabled={!cambiado || valor === '' || guardando}>
        Guardar
      </Boton>
    </form>
  )
}
 
/** Panel del administrador: como va la economia y sus reglas, editables sin tocar codigo. */
export function Administracion() {
  const { token } = useSesion()
  const [datos, setDatos] = useState(null)
  const [parametros, setParametros] = useState(null)
  const [mensaje, setMensaje] = useState(null)
 
  useEffect(() => {
    let vigente = true
    Promise.all([obtenerIndicadores(token), obtenerParametros(token)])
      .then(([nuevos, lista]) => {
        if (!vigente) return
        setDatos(nuevos)
        setParametros(lista)
      })
      .catch((e) => {
        if (vigente) setMensaje({ tipo: 'error', texto: e.message })
      })
    return () => {
      vigente = false
    }
  }, [token])
 
  async function guardar(nombre, valor) {
    setMensaje(null)
    try {
      const actualizado = await cambiarParametro(token, nombre, valor)
      setParametros((lista) => lista.map((p) => (p.nombre === nombre ? actualizado : p)))
      setMensaje({ tipo: 'exito', texto: `Se guardó ${nombre}: ahora vale ${actualizado.valor}.` })
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e.message })
    }
  }
 
  return (
    <section>
      <TituloPagina titulo="Administración" bajada="Indicadores de la economía de tokens y sus parámetros." />
      {mensaje && (
        <Aviso tipo={mensaje.tipo} className="mb-5">
          {mensaje.texto}
        </Aviso>
      )}
 
      {datos && (
        <>
          <h2 className="mb-3 text-base">Últimos {datos.dias_ventana} días</h2>
          <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Indicador titulo="Masa circulante" valor={datos.masa_circulante} ayuda="Tokens vigentes en manos de usuarios" />
            <Indicador titulo="Retenidos" valor={datos.tokens_retenidos} ayuda="Esperando una sesión o un reporte" />
            <Indicador titulo="Velocidad" valor={datos.velocidad} ayuda="Consumidos sobre masa circulante" />
            <Indicador titulo="Caducidad" valor={porcentaje(datos.tasa_caducidad)} ayuda="Vencidos sobre entregados" />
            <Indicador titulo="Cobertura gratuita" valor={porcentaje(datos.cobertura_gratuita)} ayuda="Consumo pagado con tokens gratis" />
            <Indicador titulo="Conversión" valor={porcentaje(datos.conversion)} ayuda="Usuarios activos que han comprado" />
            <Indicador titulo="Usuarios activos" valor={datos.usuarios_activos} />
            <Indicador titulo="Sesiones terminadas" valor={datos.sesiones_terminadas} />
          </div>
        </>
      )}
 
      {parametros && (
        <Tarjeta className="max-w-3xl p-6">
          <h2 className="text-base">Parámetros</h2>
          <p className="mb-2 text-xs text-tinta/65">Cada cambio rige desde la próxima operación.</p>
          <div className="divide-y divide-niebla">
            {parametros.map((parametro) => (
              <FilaParametro key={parametro.nombre} parametro={parametro} alGuardar={guardar} />
            ))}
          </div>
        </Tarjeta>
      )}
    </section>
  )
}