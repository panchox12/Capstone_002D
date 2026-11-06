import { pedir } from './cliente'
 
// Devuelve { no_leidas, avisos }.
export function obtenerNotificaciones(token) {
  return pedir('/notificaciones', { token })
}
 
export function marcarLeida(token, notificacionId) {
  return pedir(`/notificaciones/${notificacionId}/leida`, { metodo: 'POST', token })
}
 
export function marcarTodasLeidas(token) {
  return pedir('/notificaciones/leer-todas', { metodo: 'POST', token })
}