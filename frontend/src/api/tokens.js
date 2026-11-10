import { pedir } from './cliente'

// Saldo por tipo.
export function obtenerSaldo(token) {
  return pedir('/tokens/saldo', { token })
}

// Avisa que termino el video; la API decide si entrega el token.
export function registrarVideo(token) {
  return pedir('/tokens/videos', { metodo: 'POST', token })
}

// Ultimos movimientos del saldo, del mas nuevo al mas antiguo.
export function obtenerMovimientos(token, limite = 50) {
  return pedir(`/tokens/movimientos?limite=${limite}`, { token })
}