import { vi } from 'vitest'

/** Respuesta JSON como la que entrega FastAPI. */
export function respuestaJson(cuerpo, estado = 200) {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { 'content-type': 'application/json' },
  })
}

/**
 * Reemplaza fetch por una API falsa. Recibe un objeto { 'METODO /ruta': funcion }
 * y responde segun la ruta pedida; cualquier ruta no prevista falla con 404.
 */
export function simularApi(rutas) {
  const fetchFalso = vi.fn(async (url, opciones = {}) => {
    const ruta = new URL(url).pathname
    const clave = `${opciones.method ?? 'GET'} ${ruta}`
    const manejador = rutas[clave]
    return manejador ? manejador(opciones) : respuestaJson({ detail: 'Not Found' }, 404)
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

export const USUARIO_ANA = {
  id: '0b6f3c1e-0000-4000-8000-000000000001',
  correo: 'ana@duoc.cl',
  nombre_visible: 'Ana López',
  estado_cuenta: 'activa',
  consentimiento_grabacion: true,
  creado_en: '2026-09-20T12:00:00Z',
}
