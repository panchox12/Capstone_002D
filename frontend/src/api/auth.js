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
