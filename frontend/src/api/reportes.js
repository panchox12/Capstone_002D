import { pedir } from './cliente'
 
export function reportarSesion(token, sesionId, motivo, descripcion) {
  return pedir('/reportes', { metodo: 'POST', token, json: { sesion_id: sesionId, motivo, descripcion } })
}
 
export function obtenerMisReportes(token) {
  return pedir('/reportes/mios', { token })
}