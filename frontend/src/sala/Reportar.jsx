import { useState } from 'react'
import { reportarSesion } from '../api/reportes'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { claseCampo, claseEtiqueta } from '../componentes/ui/clases'
import { useSesion } from '../sesion/useSesion'
 
const MOTIVOS = [
  { valor: 'incumplimiento', texto: 'No cumplió lo acordado' },
  { valor: 'conducta', texto: 'Conducta inapropiada' },
  { valor: 'fraude', texto: 'Fraude o engaño' },
  { valor: 'otro', texto: 'Otro motivo' },
]
 
/** Reportar la sesion. La grabacion se borra a las 24 horas, salvo que haya un reporte. */
export function Reportar({ sesionId }) {
  const { token } = useSesion()
  const [abierto, setAbierto] = useState(false)
  const [motivo, setMotivo] = useState('incumplimiento')
  const [descripcion, setDescripcion] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [folio, setFolio] = useState(null)
 
  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      const reporte = await reportarSesion(token, sesionId, motivo, descripcion)
      setFolio(reporte.folio)
    } catch (e) {
      setError(e.message)
    } finally {
      setEnviando(false)
    }
  }
 
  if (folio) {
    return (
      <Aviso tipo="exito" className="mt-4">
        Recibimos tu reporte (folio {folio}). Soporte lo revisará con la grabación de la sesión.
      </Aviso>
    )
  }
 
  if (!abierto) {
    return (
      <Boton tamano="chico" variante="secundario" className="mt-4" onClick={() => setAbierto(true)}>
        Reportar un problema
      </Boton>
    )
  }
 
  return (
    <form onSubmit={enviar} className="mt-4 grid gap-3">
      <Aviso tipo="info">
        La grabación se borra 24 horas después de terminar la sesión. Si reportas antes, se guarda hasta que soporte
        resuelva, y si fue en los primeros 10 minutos, el pago al tutor queda congelado.
      </Aviso>
      <label className={claseEtiqueta}>
        Motivo
        <select className={claseCampo} value={motivo} onChange={(e) => setMotivo(e.target.value)}>
          {MOTIVOS.map((m) => (
            <option key={m.valor} value={m.valor}>
              {m.texto}
            </option>
          ))}
        </select>
      </label>
      <label className={claseEtiqueta}>
        Qué pasó
        <textarea
          className={claseCampo}
          rows={3}
          minLength={10}
          maxLength={1000}
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
        />
      </label>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <Boton type="submit" tamano="chico" className="justify-self-start" disabled={descripcion.trim().length < 10 || enviando}>
        Enviar reporte
      </Boton>
    </form>
  )
}