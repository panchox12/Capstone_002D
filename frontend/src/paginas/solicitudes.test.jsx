import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import App from '../App'
import { respuestaJson, simularApi, USUARIO_ANA } from '../pruebas/apiFalsa'
import { SesionProvider } from '../sesion/SesionProvider'
 
function abrirEn(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <SesionProvider>
        <App />
      </SesionProvider>
    </MemoryRouter>,
  )
}
 
function conSesion(rutas) {
  localStorage.setItem('cachai_token', 'token-de-ana')
  return simularApi({ 'GET /auth/yo': () => respuestaJson(USUARIO_ANA), ...rutas })
}
 
const RODRIGO = { id: 'tutor-1', nombre_visible: 'Rodrigo Salas' }
const ANA = { id: USUARIO_ANA.id, nombre_visible: 'Ana López' }
 
function resultado(cambios = {}) {
  return {
    habilidad_id: 'hab-1',
    tema_id: 6,
    tema_nombre: 'Instalaciones eléctricas domiciliarias',
    ruta: 'Oficios > Electricidad',
    puntaje: 0.62,
    precio_por_bloque: 3,
    tutor_id: RODRIGO.id,
    tutor_nombre: RODRIGO.nombre_visible,
    reputacion_promedio: null,
    total_evaluaciones: 0,
    en_linea: true,
    ...cambios,
  }
}
 
function solicitud(cambios = {}) {
  return {
    id: 'sol-1',
    estado: 'pendiente',
    modalidad: 'en_vivo',
    mensaje: 'Se me corta la luz',
    precio_bloque: 3,
    tema_nombre: 'Instalaciones eléctricas domiciliarias',
    aprendiz: ANA,
    tutor: RODRIGO,
    fecha_envio: '2026-10-28T12:00:00Z',
    fecha_limite_respuesta: '2026-10-28T12:05:00Z',
    fecha_resolucion: null,
    segundos_restantes: 290,
    ...cambios,
  }
}
 
describe('buscador', () => {
  it('muestra a quien sabe del tema y si todavia no tiene valoraciones', async () => {
    const fetchFalso = conSesion({ 'GET /buscar': () => respuestaJson({ modo: 'semantico', resultados: [resultado()] }) })
    const usuario = userEvent.setup()
    abrirEn('/buscar')
 
    await usuario.type(await screen.findByLabelText('Tu duda'), 'tengo un problema con un enchufe')
    await usuario.click(screen.getByRole('button', { name: 'Buscar' }))
 
    expect(await screen.findByRole('heading', { name: 'Rodrigo Salas' })).toBeInTheDocument()
    expect(screen.getByText('Usuario nuevo')).toBeInTheDocument()
    expect(screen.getByText('En línea')).toBeInTheDocument()
    const [url] = fetchFalso.mock.calls.find(([u]) => u.includes('/buscar'))
    expect(new URL(url).searchParams.get('q')).toBe('tengo un problema con un enchufe')
  })
 
  it('pedir ayuda envia la solicitud con el mensaje y lleva a Solicitudes', async () => {
    const fetchFalso = conSesion({
      'GET /buscar': () => respuestaJson({ modo: 'semantico', resultados: [resultado()] }),
      'POST /solicitudes': () => respuestaJson(solicitud(), 201),
      'GET /solicitudes/recibidas': () => respuestaJson([]),
      'GET /solicitudes/enviadas': () => respuestaJson([solicitud()]),
    })
    const usuario = userEvent.setup()
    abrirEn('/buscar')
 
    await usuario.type(await screen.findByLabelText('Tu duda'), 'se me corta la luz')
    await usuario.click(screen.getByRole('button', { name: 'Buscar' }))
    await usuario.click(await screen.findByRole('button', { name: 'Pedir ayuda a Rodrigo Salas' }))
    await usuario.click(screen.getByRole('button', { name: 'Enviar solicitud' }))
 
    expect(await screen.findByRole('heading', { name: 'Solicitudes' })).toBeInTheDocument()
    expect(screen.getByText('Le enviaste tu duda a Rodrigo Salas. Tiene 5 minutos para responder.')).toBeInTheDocument()
    const [, opciones] = fetchFalso.mock.calls.find(([u, op]) => u.endsWith('/solicitudes') && op.method === 'POST')
    expect(JSON.parse(opciones.body)).toEqual({ habilidad_id: 'hab-1', mensaje: 'se me corta la luz' })
  })
 
  it('si nadie coincide lo dice', async () => {
    conSesion({ 'GET /buscar': () => respuestaJson({ modo: 'semantico', resultados: [] }) })
    const usuario = userEvent.setup()
    abrirEn('/buscar')
 
    await usuario.type(await screen.findByLabelText('Tu duda'), 'astrofisica cuantica')
    await usuario.click(screen.getByRole('button', { name: 'Buscar' }))
 
    expect(await screen.findByText(/No encontramos a nadie/)).toBeInTheDocument()
  })
})
 
describe('solicitudes', () => {
  it('el tutor ve el tiempo que le queda y puede aceptar', async () => {
    let recibidas = [solicitud()]
    const fetchFalso = conSesion({
      'GET /solicitudes/recibidas': () => respuestaJson(recibidas),
      'GET /solicitudes/enviadas': () => respuestaJson([]),
      'POST /solicitudes/sol-1/aceptar': () => {
        recibidas = [solicitud({ estado: 'aceptada', segundos_restantes: 0 })]
        return respuestaJson(recibidas[0])
      },
    })
    const usuario = userEvent.setup()
    abrirEn('/solicitudes')
 
    const tarjeta = (await screen.findByText(/de Ana López/)).closest('article')
    expect(within(tarjeta).getByText(/quedan 4:50 para responder/)).toBeInTheDocument()
    await usuario.click(within(tarjeta).getByRole('button', { name: 'Aceptar' }))
 
    expect(await screen.findByText(/La sala ya está abierta/)).toBeInTheDocument()
    expect(fetchFalso.mock.calls.some(([u, op]) => u.endsWith('/sol-1/aceptar') && op.method === 'POST')).toBe(true)
    expect(await screen.findByText('Aceptada')).toBeInTheDocument()
  })
 
  it('el aprendiz puede cancelar una solicitud pendiente', async () => {
    const fetchFalso = conSesion({
      'GET /solicitudes/recibidas': () => respuestaJson([]),
      'GET /solicitudes/enviadas': () => respuestaJson([solicitud({ modalidad: 'diferida', segundos_restantes: 86000 })]),
      'POST /solicitudes/sol-1/cancelar': () => respuestaJson(solicitud({ estado: 'cancelada' })),
    })
    const usuario = userEvent.setup()
    abrirEn('/solicitudes')
 
    expect(await screen.findByText(/quedan 23 h 53 min/)).toBeInTheDocument()
    await usuario.click(screen.getByRole('button', { name: 'Cancelar solicitud' }))
 
    expect(await screen.findByText(/Cancelaste la solicitud/)).toBeInTheDocument()
    expect(fetchFalso.mock.calls.some(([u]) => u.endsWith('/sol-1/cancelar'))).toBe(true)
  })
 
  it('los errores de la API se muestran tal cual', async () => {
    conSesion({
      'GET /solicitudes/recibidas': () => respuestaJson([solicitud()]),
      'GET /solicitudes/enviadas': () => respuestaJson([]),
      'POST /solicitudes/sol-1/aceptar': () =>
        respuestaJson({ detail: 'Se acabo el tiempo para responder esta solicitud' }, 409),
    })
    const usuario = userEvent.setup()
    abrirEn('/solicitudes')
 
    await usuario.click(await screen.findByRole('button', { name: 'Aceptar' }))
 
    expect(await screen.findByRole('alert')).toHaveTextContent('Se acabo el tiempo para responder esta solicitud')
  })
})