import { useState } from 'react'
import { proponerExtension, responderExtension, terminarSesion } from '../api/sesiones'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton } from '../componentes/ui/Boton'
import { useSesion } from '../sesion/useSesion'
import { plural } from '../utilidades/formato'
 
/**
 * Lo que se puede hacer durante la sesion: pedir un bloque mas (lo acepta el otro)
 * y terminar antes. Cada accion devuelve la sesion actualizada por el servidor.
 */
export function Controles({ sesion, otra, alCambiar }) {
  const { token, usuario } = useSesion()
  const [ocupado, setOcupado] = useState(false)
  const [confirmarTermino, setConfirmarTermino] = useState(false)
  const [error, setError] = useState(null)
 
  async function ejecutar(accion) {
    setError(null)
    setOcupado(true)
    try {
      alCambiar(await accion())
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
      setConfirmarTermino(false)
    }
  }
 
  const enCurso = sesion.estado === 'en_curso'
  const propuesta = sesion.extension_propuesta_por
  const soyAprendiz = sesion.aprendiz.id === usuario?.id
  const costo = plural(sesion.precio_bloque, 'token', 'tokens')
 
  return (
    <div className="mt-4 grid gap-3">
      {enCurso && !propuesta && (
        <Boton
          tamano="chico"
          variante="secundario"
          className="justify-self-start"
          disabled={ocupado}
          onClick={() => ejecutar(() => proponerExtension(token, sesion.id))}
        >
          Proponer un bloque más ({costo})
        </Boton>
      )}
 
      {enCurso && propuesta === usuario?.id && (
        <div className="flex flex-wrap items-center gap-2">
          <p className="mr-2 text-sm">Esperando que {otra.nombre_visible} acepte un bloque más.</p>
          <Boton
            tamano="chico"
            variante="secundario"
            disabled={ocupado}
            onClick={() => ejecutar(() => responderExtension(token, sesion.id, 'rechazar'))}
          >
            Retirar
          </Boton>
        </div>
      )}
 
      {enCurso && propuesta && propuesta !== usuario?.id && (
        <Aviso tipo="info">
          {otra.nombre_visible} propone un bloque más de 15 minutos
          {soyAprendiz ? `: se descuentan ${costo} de tu saldo.` : '.'}
          <span className="mt-2 flex gap-2">
            <Boton
              tamano="chico"
              disabled={ocupado}
              onClick={() => ejecutar(() => responderExtension(token, sesion.id, 'aceptar'))}
            >
              Aceptar
            </Boton>
            <Boton
              tamano="chico"
              variante="secundario"
              disabled={ocupado}
              onClick={() => ejecutar(() => responderExtension(token, sesion.id, 'rechazar'))}
            >
              Rechazar
            </Boton>
          </span>
        </Aviso>
      )}
 
      {confirmarTermino ? (
        <div className="flex flex-wrap items-center gap-2">
          <p className="mr-2 text-sm">
            {enCurso
              ? '¿Terminar ahora? El bloque que ya empezó se cobra completo.'
              : '¿Cancelar la sesión? Nadie paga nada.'}
          </p>
          <Boton tamano="chico" disabled={ocupado} onClick={() => ejecutar(() => terminarSesion(token, sesion.id))}>
            Sí, {enCurso ? 'terminar' : 'cancelar'}
          </Boton>
          <Boton tamano="chico" variante="secundario" onClick={() => setConfirmarTermino(false)}>
            No
          </Boton>
        </div>
      ) : (
        <Boton
          tamano="chico"
          variante="secundario"
          className="justify-self-start"
          onClick={() => setConfirmarTermino(true)}
        >
          {enCurso ? 'Terminar sesión' : 'Cancelar sesión'}
        </Boton>
      )}
 
      {error && <Aviso tipo="error">{error}</Aviso>}
    </div>
  )
}