import { pedir } from './cliente'
 
export function obtenerMiValoracion(token, sesionId) {
  return pedir(`/valoraciones/sesion/${sesionId}`, { token })
}
 
export function valorarSesion(token, sesionId, estrellas, comentario) {
  return pedir('/valoraciones', { metodo: 'POST', token, json: { sesion_id: sesionId, estrellas, comentario } })
}