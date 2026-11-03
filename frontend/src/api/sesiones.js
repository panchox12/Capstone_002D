import { pedir } from './cliente'

export function obtenerSesiones(token) {
  return pedir('/sesiones', { token })
}

export function obtenerSesion(token, sesionId) {
  return pedir(`/sesiones/${sesionId}`, { token })
}

// Devuelve { url, token, nombre_sala }: el permiso de LiveKit para entrar a la sala.
export function entrarASala(token, sesionId) {
  return pedir(`/sesiones/${sesionId}/entrar`, { metodo: 'POST', token })
}