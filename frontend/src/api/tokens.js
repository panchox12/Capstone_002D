import { pedir } from './cliente'

// Saldo por tipo.
export function obtenerSaldo(token) {
  return pedir('/tokens/saldo', { token })
}

// Avisa que termino el video; la API decide si entrega el token.
export function registrarVideo(token) {
  return pedir('/tokens/videos', { metodo: 'POST', token })
}