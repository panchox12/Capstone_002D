import { pedir } from './cliente'
 
// El servidor decide si es en vivo o diferida segun la presencia del tutor.
export function enviarSolicitud(token, habilidadId, mensaje) {
  return pedir('/solicitudes', { metodo: 'POST', token, json: { habilidad_id: habilidadId, mensaje } })
}
 
export function obtenerEnviadas(token) {
  return pedir('/solicitudes/enviadas', { token })
}
 
export function obtenerRecibidas(token) {
  return pedir('/solicitudes/recibidas', { token })
}
 
// accion: aceptar, rechazar o cancelar.
export function responderSolicitud(token, solicitudId, accion) {
  return pedir(`/solicitudes/${solicitudId}/${accion}`, { metodo: 'POST', token })
}