import { pedir } from './cliente'
 
export function obtenerIndicadores(token) {
  return pedir('/admin/indicadores', { token })
}
 
export function obtenerParametros(token) {
  return pedir('/admin/parametros', { token })
}
 
export function cambiarParametro(token, nombre, valor) {
  return pedir(`/admin/parametros/${nombre}`, { metodo: 'PUT', token, json: { valor } })
}