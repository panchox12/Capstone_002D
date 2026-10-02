/*
 * Unico punto de contacto con la API: todas las peticiones pasan por aca.
 * Si mañana cambia la direccion de la API o la forma de autenticar,
 * se cambia en este archivo y en ningun otro.
 */

const URL_API = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

/** Error con el codigo HTTP, para que cada pantalla decida que mostrar. */
export class ErrorApi extends Error {
  constructor(estado, mensaje) {
    super(mensaje)
    this.name = 'ErrorApi'
    this.estado = estado
  }
}

// La sesion se registra aca para enterarse cuando el token deja de servir.
let alExpirarSesion = null

export function registrarAlExpirarSesion(funcion) {
  alExpirarSesion = funcion
}

function mensajeDeError(cuerpo, estado) {
  const detalle = cuerpo?.detail
  if (typeof detalle === 'string') return detalle
  // FastAPI responde una lista cuando los datos no pasan la validacion (422)
  if (Array.isArray(detalle) && detalle.length > 0) {
    return detalle.map((error) => error.msg).join('. ')
  }
  return `La API respondió con el error ${estado}`
}

export async function pedir(ruta, { metodo = 'GET', json, formulario, token } = {}) {
  const cabeceras = {}
  let cuerpo

  if (json !== undefined) {
    cabeceras['Content-Type'] = 'application/json'
    cuerpo = JSON.stringify(json)
  } else if (formulario !== undefined) {
    // El navegador agrega solo la cabecera application/x-www-form-urlencoded
    cuerpo = new URLSearchParams(formulario)
  }
  if (token) {
    cabeceras.Authorization = `Bearer ${token}`
  }

  let respuesta
  try {
    respuesta = await fetch(`${URL_API}${ruta}`, { method: metodo, headers: cabeceras, body: cuerpo })
  } catch {
    throw new ErrorApi(0, 'No se pudo conectar con la API. Revisa que el backend esté corriendo.')
  }

  const esJson = (respuesta.headers.get('content-type') ?? '').includes('application/json')
  const datos = esJson ? await respuesta.json() : null

  if (!respuesta.ok) {
    // Un 401 con token significa que el token vencio o no es valido
    if (respuesta.status === 401 && token && alExpirarSesion) {
      alExpirarSesion()
    }
    throw new ErrorApi(respuesta.status, mensajeDeError(datos, respuesta.status))
  }
  return datos
}
