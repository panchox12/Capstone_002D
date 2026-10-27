import { pedir } from './cliente'

/** El login de la API sigue el estandar OAuth2: formulario con username y password, no JSON. */
export function iniciarSesion(correo, contrasena) {
  return pedir('/auth/login', {
    metodo: 'POST',
    formulario: { username: correo, password: contrasena },
  })
}

export function obtenerUsuarioActual(token) {
  return pedir('/auth/yo', { token })
}

export function registrar(datos) {
  return pedir('/auth/registro', { metodo: 'POST', json: datos })
}

/** El token viene en el enlace del correo; la API lo valida y activa la cuenta. */
export function confirmarCorreo(tokenConfirmacion) {
  return pedir(`/auth/confirmar/${encodeURIComponent(tokenConfirmacion)}`)
}
