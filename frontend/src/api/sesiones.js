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

export function proponerExtension(token, sesionId) {
  return pedir(`/sesiones/${sesionId}/extension`, { metodo: 'POST', token })
}
 
// respuesta: aceptar o rechazar. Rechazar tambien sirve para retirar la propia.
export function responderExtension(token, sesionId, respuesta) {
  return pedir(`/sesiones/${sesionId}/extension/${respuesta}`, { metodo: 'POST', token })
}
 
export function terminarSesion(token, sesionId) {
  return pedir(`/sesiones/${sesionId}/terminar`, { metodo: 'POST', token })
}