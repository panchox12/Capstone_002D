import { afterEach, describe, expect, it, vi } from 'vitest'
import { respuestaJson, simularApi } from '../pruebas/apiFalsa'
import { iniciarSesion } from './auth'
import { ErrorApi, pedir, registrarAlExpirarSesion } from './cliente'

describe('cliente de la API', () => {
  afterEach(() => registrarAlExpirarSesion(null))

  it('envia el token en la cabecera Authorization', async () => {
    const fetchFalso = simularApi({ 'GET /auth/yo': () => respuestaJson({ ok: true }) })

    await pedir('/auth/yo', { token: 'abc123' })

    const [, opciones] = fetchFalso.mock.calls[0]
    expect(opciones.headers.Authorization).toBe('Bearer abc123')
  })

  it('el login viaja como formulario OAuth2, no como JSON', async () => {
    const fetchFalso = simularApi({
      'POST /auth/login': () => respuestaJson({ access_token: 't', token_type: 'bearer' }),
    })

    await iniciarSesion('ana@duoc.cl', 'clave12345')

    const [, opciones] = fetchFalso.mock.calls[0]
    expect(opciones.body).toBeInstanceOf(URLSearchParams)
    expect(opciones.body.get('username')).toBe('ana@duoc.cl')
    expect(opciones.body.get('password')).toBe('clave12345')
  })

  it('entrega el mensaje de error que manda FastAPI', async () => {
    simularApi({ 'GET /perfiles/nadie': () => respuestaJson({ detail: 'Perfil no encontrado' }, 404) })

    const error = await pedir('/perfiles/nadie').catch((e) => e)

    expect(error).toBeInstanceOf(ErrorApi)
    expect(error.estado).toBe(404)
    expect(error.message).toBe('Perfil no encontrado')
  })

  it('junta los mensajes cuando FastAPI rechaza los datos (422)', async () => {
    simularApi({
      'POST /habilidades': () =>
        respuestaJson({ detail: [{ msg: 'Campo requerido' }, { msg: 'Debe ser mayor que 0' }] }, 422),
    })

    const error = await pedir('/habilidades', { metodo: 'POST', json: {} }).catch((e) => e)

    expect(error.message).toBe('Campo requerido. Debe ser mayor que 0')
  })

  it('avisa con un mensaje claro si la API no esta corriendo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const error = await pedir('/temas').catch((e) => e)

    expect(error.estado).toBe(0)
    expect(error.message).toMatch(/No se pudo conectar/)
  })

  it('cierra la sesion cuando un token es rechazado con 401', async () => {
    simularApi({ 'GET /auth/yo': () => respuestaJson({ detail: 'No se pudo validar' }, 401) })
    const alExpirar = vi.fn()
    registrarAlExpirarSesion(alExpirar)

    await pedir('/auth/yo', { token: 'vencido' }).catch(() => {})

    expect(alExpirar).toHaveBeenCalledOnce()
  })
})
