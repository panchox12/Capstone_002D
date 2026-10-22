import { pedir } from './cliente'

/** Cada cuanto el navegador avisa que el usuario sigue en Cachai. La marca en Redis dura 70 segundos. */
export const MILISEGUNDOS_ENTRE_LATIDOS = 30_000

export function enviarLatido(token) {
  return pedir('/presencia/latido', { metodo: 'POST', token })
}

export function avisarDesconexion(token) {
  return pedir('/presencia', { metodo: 'DELETE', token })
}
