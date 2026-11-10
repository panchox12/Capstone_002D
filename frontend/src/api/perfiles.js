import { pedir } from './cliente'


// Publico: se busca por alias o por el id del usuario.
export function obtenerPerfil(identificador) {
  return pedir(`/perfiles/${encodeURIComponent(identificador)}`)
}
 
// cambios: biografia, enlace_personalizado o los dos.
export function guardarPerfil(token, cambios) {
  return pedir('/perfiles/mio', { metodo: 'PATCH', token, json: cambios })
}

// Preferencias de presencia: aparecer conectado y recibir solicitudes estando fuera.
export function obtenerPreferencias(token) {
  return pedir('/perfiles/mio/preferencias', { token })
}

export function guardarPreferencias(token, cambios) {
  return pedir('/perfiles/mio/preferencias', { metodo: 'PATCH', token, json: cambios })
}