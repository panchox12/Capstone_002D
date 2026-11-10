import { pedir } from './cliente'
 
export function obtenerMisHabilidades(token) {
  return pedir('/habilidades/mias', { token })
}
 
export function publicarHabilidad(token, temaId, precio) {
  return pedir('/habilidades', { metodo: 'POST', token, json: { tema_id: temaId, precio_por_bloque: precio } })
}
 
// cambios: precio_por_bloque, estado o los dos.
export function actualizarHabilidad(token, habilidadId, cambios) {
  return pedir(`/habilidades/${habilidadId}`, { metodo: 'PATCH', token, json: cambios })
}