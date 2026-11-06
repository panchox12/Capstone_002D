import { pedir } from './cliente'
 
export function obtenerReportes(token, estado) {
  const filtro = estado ? `?estado=${estado}` : ''
  return pedir(`/soporte/reportes${filtro}`, { token })
}
 
export function obtenerReporte(token, reporteId) {
  return pedir(`/soporte/reportes/${reporteId}`, { token })
}
 
// Cada apertura queda en la bitacora: por eso es POST.
export function abrirGrabacion(token, reporteId) {
  return pedir(`/soporte/reportes/${reporteId}/grabacion`, { metodo: 'POST', token })
}
 
export function obtenerAccesos(token, reporteId) {
  return pedir(`/soporte/reportes/${reporteId}/accesos`, { token })
}
 
export function resolverReporte(token, reporteId, resolucion) {
  return pedir(`/soporte/reportes/${reporteId}/resolver`, { metodo: 'POST', token, json: resolucion })
}