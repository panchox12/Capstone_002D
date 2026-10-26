import { pedir } from './cliente'

export function obtenerEstadoVerificacion(token) {
  return pedir('/verificacion/estado', { token })
}

/**
 * Envia las tres imagenes en base64, sin el prefijo "data:image/...;base64,".
 * La API las procesa en memoria y no guarda ninguna.
 */
export function verificarIdentidad(token, { documentoFrontal, documentoReverso, rostro }) {
  return pedir('/verificacion', {
    metodo: 'POST',
    token,
    json: {
      documento_frontal: documentoFrontal,
      documento_reverso: documentoReverso,
      rostro,
      consentimiento_biometrico: true,
    },
  })
}
