import { useEffect, useState } from 'react'
import { obtenerReportes } from '../api/soporte'
import { Aviso } from '../componentes/ui/Aviso'
import { BotonEnlace } from '../componentes/ui/Boton'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { useSesion } from '../sesion/useSesion'
import { ESTADOS_REPORTE, MOTIVOS_REPORTE } from '../soporte/textos'
import { fechaCorta } from '../utilidades/formato'
 
const FILTROS = [
  { valor: 'abierto', texto: 'Abiertos' },
  { valor: '', texto: 'Todos' },
]
 
/** Bandeja de soporte: los reportes, primero los mas nuevos. */
export function Soporte() {
  const { token } = useSesion()
  const [filtro, setFiltro] = useState('abierto')
  const [reportes, setReportes] = useState(null)
  const [error, setError] = useState(null)
 
  useEffect(() => {
    let vigente = true
    obtenerReportes(token, filtro)
      .then((lista) => {
        if (vigente) setReportes(lista)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [token, filtro])
 
  return (
    <section className="max-w-4xl">
      <TituloPagina titulo="Soporte" bajada="Reportes de sesiones para revisar y resolver." />
      <div className="mb-4 flex gap-2" role="group" aria-label="Filtro">
        {FILTROS.map((f) => (
          <button
            key={f.valor}
            type="button"
            aria-pressed={filtro === f.valor}
            onClick={() => setFiltro(f.valor)}
            className={`rounded-full px-4 py-1.5 text-[12.5px] font-semibold ${filtro === f.valor ? 'bg-oceano text-white' : 'bg-niebla text-tinta'}`}
          >
            {f.texto}
          </button>
        ))}
      </div>
      {error && <Aviso tipo="error">{error}</Aviso>}
      {reportes !== null && reportes.length === 0 && <p className="text-sm text-tinta/65">No hay reportes aquí.</p>}
      {reportes !== null && reportes.length > 0 && (
        <div className="grid gap-3">
          {reportes.map((reporte) => {
            const estado = ESTADOS_REPORTE[reporte.estado]
            return (
              <Tarjeta key={reporte.id} como="article" className="flex flex-wrap items-center gap-3 p-5">
                <div className="mr-auto">
                  <h3 className="text-[15px]">
                    Folio {reporte.folio} · {MOTIVOS_REPORTE[reporte.motivo]}
                  </h3>
                  <p className="mt-1 text-xs text-tinta/65">
                    {reporte.reportante.nombre_visible} reporta a {reporte.reportado.nombre_visible} · {reporte.tema_nombre} ·{' '}
                    {fechaCorta(reporte.creado_en)}
                  </p>
                </div>
                {reporte.congela_pago && reporte.estado === 'abierto' && <Ficha variante="contorno">Pago congelado</Ficha>}
                <Ficha variante={estado.variante}>{estado.texto}</Ficha>
                <BotonEnlace to={`/soporte/${reporte.id}`} tamano="chico" variante="secundario">
                  Revisar
                </BotonEnlace>
              </Tarjeta>
            )
          })}
        </div>
      )}
    </section>
  )
}