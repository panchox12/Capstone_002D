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
  return simularApi({
    'GET /auth/yo': () => respuestaJson(USUARIO_ANA),
    'GET /tokens/saldo': () => respuestaJson({ gratis: 7, pagado: 0, total: 7, retenidos: 0, lotes: [] }),
    ...rutas,
  })
}
 
const ANA = { id: USUARIO_ANA.id, nombre_visible: 'Ana López' }
const RODRIGO = { id: 'tutor-1', nombre_visible: 'Rodrigo Salas' }
 
const TERMINADA = {
  id: 'ses-1',
  solicitud_id: 'sol-1',
  estado: 'terminada',
  tema_nombre: 'Álgebra',
  precio_bloque: 3,
  aprendiz: ANA,
  tutor: RODRIGO,
  fecha_apertura_sala: '2026-11-03T12:00:00Z',
  fecha_limite_conexion: '2026-11-03T12:05:00Z',
  fecha_conexion_ambos: '2026-11-03T12:01:00Z',
  fecha_cierre: '2026-11-03T12:16:00Z',
  bloques_cobrados: 1,
  motivo_cierre: 'termino el tiempo pagado',
  segundos_para_conectarse: 0,
  segundos_restantes_bloque: 0,
  extension_propuesta_por: null,
  pausa_activa: false,
  usuario_caido_id: null,
  segundos_para_reconectar: 0,
  pausas_usadas: 0,
  pausas_maximas: 3,
}
 
describe('valorar al terminar', () => {
  it('elige estrellas, comenta y envia', async () => {
    const fetchFalso = conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(TERMINADA),
      'GET /valoraciones/sesion/ses-1': () => respuestaJson({ valorada: false, valoracion: null }),
      'POST /valoraciones': (op) =>
        respuestaJson({ ...JSON.parse(op.body), creado_en: '2026-11-03T12:20:00Z' }, 201),
    })
    const usuario = userEvent.setup()
    abrirEn('/sesiones/ses-1')
 
    const enviar = await screen.findByRole('button', { name: 'Enviar valoración' })
    expect(enviar).toBeDisabled()
    await usuario.click(screen.getByRole('radio', { name: '4 estrellas' }))
    await usuario.type(screen.getByLabelText('Comentario (opcional)'), 'Muy claro')
    await usuario.click(enviar)
 
    expect(await screen.findByText('Tu valoración de Rodrigo Salas')).toBeInTheDocument()
    const [, opciones] = fetchFalso.mock.calls.find(([url, op]) => url.endsWith('/valoraciones') && op.method === 'POST')
    expect(JSON.parse(opciones.body)).toEqual({ sesion_id: 'ses-1', estrellas: 4, comentario: 'Muy claro' })
  })
 
  it('si ya valoro muestra sus estrellas sin formulario', async () => {
    conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(TERMINADA),
      'GET /valoraciones/sesion/ses-1': () =>
        respuestaJson({
          valorada: true,
          valoracion: { sesion_id: 'ses-1', estrellas: 5, comentario: null, creado_en: '2026-11-03T12:20:00Z' },
        }),
    })
    abrirEn('/sesiones/ses-1')
 
    const grupo = await screen.findByRole('radiogroup')
    expect(within(grupo).getByRole('radio', { name: '5 estrellas' })).toHaveAttribute('aria-checked', 'true')
    expect(screen.queryByRole('button', { name: 'Enviar valoración' })).not.toBeInTheDocument()
  })
 
  it('una sesion cancelada no se valora', async () => {
    conSesion({
      'GET /sesiones/ses-1': () =>
        respuestaJson({ ...TERMINADA, estado: 'cancelada', fecha_conexion_ambos: null, bloques_cobrados: 0 }),
    })
    abrirEn('/sesiones/ses-1')
 
    expect(await screen.findByText('Resumen')).toBeInTheDocument()
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument()
  })
})
 
describe('bloqueos', () => {
  it('bloquear pide confirmacion antes', async () => {
    const fetchFalso = conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(TERMINADA),
      'GET /valoraciones/sesion/ses-1': () => respuestaJson({ valorada: false, valoracion: null }),
      'POST /bloqueos': () => new Response(null, { status: 204 }),
    })
    const usuario = userEvent.setup()
    abrirEn('/sesiones/ses-1')
 
    await usuario.click(await screen.findByRole('button', { name: 'Bloquear a Rodrigo Salas' }))
    await usuario.click(screen.getByRole('button', { name: 'Sí, bloquear' }))
 
    expect(await screen.findByText(/Bloqueaste a Rodrigo Salas/)).toBeInTheDocument()
    const [, opciones] = fetchFalso.mock.calls.find(([url, op]) => url.endsWith('/bloqueos') && op.method === 'POST')
    expect(JSON.parse(opciones.body)).toEqual({ usuario_id: 'tutor-1' })
  })
 
  it('en mi cuenta se ve la lista y se puede desbloquear', async () => {
    conSesion({
      'GET /verificacion/estado': () => respuestaJson({ verificado: true }),
      'GET /perfiles/mio/preferencias': () => respuestaJson({ mostrar_en_linea: true, acepta_diferidas: true }),
      'GET /bloqueos': () =>
        respuestaJson([{ usuario_id: 'u-9', nombre_visible: 'Diego Contreras', desde: '2026-11-02T10:00:00Z' }]),
      'DELETE /bloqueos/u-9': () => new Response(null, { status: 204 }),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    expect(await screen.findByText('Diego Contreras')).toBeInTheDocument()
    await usuario.click(screen.getByRole('button', { name: 'Desbloquear' }))
 
    expect(await screen.findByText('No has bloqueado a nadie.')).toBeInTheDocument()
  })
})