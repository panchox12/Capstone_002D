import { pedir } from './cliente'

// Preferencias de presencia: aparecer conectado y recibir solicitudes estando fuera.
export function obtenerPreferencias(token) {
  return pedir('/perfiles/mio/preferencias', { token })
}

export function guardarPreferencias(token, cambios) {
  return pedir('/perfiles/mio/preferencias', { metodo: 'PATCH', token, json: cambios })
}