import { pedir } from './cliente'
 
export function obtenerBloqueados(token) {
  return pedir('/bloqueos', { token })
}
 
export function bloquearUsuario(token, usuarioId) {
  return pedir('/bloqueos', { metodo: 'POST', token, json: { usuario_id: usuarioId } })
}
 
export function desbloquearUsuario(token, usuarioId) {
  return pedir(`/bloqueos/${usuarioId}`, { metodo: 'DELETE', token })
}