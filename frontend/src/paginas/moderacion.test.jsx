import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import App from '../App'
import { respuestaJson, simularApi, USUARIO_ANA } from '../pruebas/apiFalsa'
import { SesionProvider } from '../sesion/SesionProvider'
 
vi.mock('../sala/VideoLlamada', () => ({ VideoLlamada: () => <div data-testid="videollamada" /> }))
 
function abrirEn(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <SesionProvider>
        <App />
      </SesionProvider>
    </MemoryRouter>,
  )
}
 
function conSesion(rutas, rol = 'usuario') {
  localStorage.setItem('cachai_token', 'token-de-ana')
  return simularApi({
    'GET /auth/yo': () => respuestaJson({ ...USUARIO_ANA, rol }),
    'GET /tokens/saldo': () => respuestaJson({ gratis: 7, pagado: 0, total: 7, retenidos: 3, lotes: [] }),
    ...rutas,
  })
}
 
function llamadas(fetchFalso, metodo, final) {
  return fetchFalso.mock.calls.filter(([url, op]) => (op?.method ?? 'GET') === metodo && url.endsWith(final))
}
 
const ANA = { id: USUARIO_ANA.id, nombre_visible: 'Ana López' }
const RODRIGO = { id: 'tutor-1', nombre_visible: 'Rodrigo Salas' }
 
function sesion(cambios = {}) {
  return {
    id: 'ses-1',
    solicitud_id: 'sol-1',
    estado: 'en_curso',
    tema_nombre: 'Álgebra',
    precio_bloque: 3,
    aprendiz: ANA,
    tutor: RODRIGO,
    fecha_apertura_sala: '2026-11-03T12:00:00Z',
    fecha_limite_conexion: '2026-11-03T12:05:00Z',
    fecha_conexion_ambos: '2026-11-03T12:01:00Z',
    fecha_cierre: null,
    bloques_cobrados: 1,
    motivo_cierre: null,
    segundos_para_conectarse: 0,
    segundos_restantes_bloque: 600,
    extension_propuesta_por: null,
    pausa_activa: false,
    usuario_caido_id: null,
    segundos_para_reconectar: 0,
    pausas_usadas: 0,
    pausas_maximas: 3,
    ...cambios,
  }
}
 
describe('controles de la sala', () => {
  it('proponer un bloque mas deja la propuesta esperando al otro', async () => {
    const fetchFalso = conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(sesion()),
      'POST /sesiones/ses-1/extension': () => respuestaJson(sesion({ extension_propuesta_por: ANA.id })),
    })
    const usuario = userEvent.setup()
    abrirEn('/sesiones/ses-1')
 
    await usuario.click(await screen.findByRole('button', { name: 'Proponer un bloque más (3 tokens)' }))
 
    expect(await screen.findByText('Esperando que Rodrigo Salas acepte un bloque más.')).toBeInTheDocument()
    expect(llamadas(fetchFalso, 'POST', '/extension')).toHaveLength(1)
  })
 
  it('si la propone el otro, el aprendiz ve el costo y acepta', async () => {
    const fetchFalso = conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(sesion({ extension_propuesta_por: RODRIGO.id })),
      'POST /sesiones/ses-1/extension/aceptar': () =>
        respuestaJson(sesion({ bloques_cobrados: 2, segundos_restantes_bloque: 1500 })),
    })
    const usuario = userEvent.setup()
    abrirEn('/sesiones/ses-1')
 
    expect(await screen.findByText(/se descuentan 3 tokens de tu saldo/)).toBeInTheDocument()
    await usuario.click(screen.getByRole('button', { name: 'Aceptar' }))
 
    expect(await screen.findByText('25:00')).toBeInTheDocument()
    expect(llamadas(fetchFalso, 'POST', '/extension/aceptar')).toHaveLength(1)
  })
 
  it('terminar pide confirmacion y avisa que el bloque se cobra', async () => {
    const fetchFalso = conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(sesion()),
      'POST /sesiones/ses-1/terminar': () =>
        respuestaJson(sesion({ estado: 'terminada', motivo_cierre: 'el aprendiz termino la sesion' })),
      'GET /valoraciones/sesion/ses-1': () => respuestaJson({ valorada: false, valoracion: null }),
    })
    const usuario = userEvent.setup()
    abrirEn('/sesiones/ses-1')
 
    await usuario.click(await screen.findByRole('button', { name: 'Terminar sesión' }))
    expect(screen.getByText(/El bloque que ya empezó se cobra completo/)).toBeInTheDocument()
    await usuario.click(screen.getByRole('button', { name: 'Sí, terminar' }))
 
    expect(await screen.findByText('Motivo de cierre: el aprendiz termino la sesion.')).toBeInTheDocument()
    expect(llamadas(fetchFalso, 'POST', '/terminar')).toHaveLength(1)
  })
})
 
describe('reportar', () => {
  it('advierte la vigencia de la grabacion y envia el reporte', async () => {
    const fetchFalso = conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(sesion({ estado: 'terminada', fecha_cierre: '2026-11-03T12:16:00Z' })),
      'GET /valoraciones/sesion/ses-1': () => respuestaJson({ valorada: false, valoracion: null }),
      'POST /reportes': () => respuestaJson({ id: 'rep-1', folio: 1004 }, 201),
    })
    const usuario = userEvent.setup()
    abrirEn('/sesiones/ses-1')
 
    await usuario.click(await screen.findByRole('button', { name: 'Reportar un problema' }))
    expect(screen.getByText(/La grabación se borra 24 horas después/)).toBeInTheDocument()
    await usuario.selectOptions(screen.getByLabelText('Motivo'), 'conducta')
    await usuario.type(screen.getByLabelText('Qué pasó'), 'Me trató mal durante la llamada')
    await usuario.click(screen.getByRole('button', { name: 'Enviar reporte' }))
 
    expect(await screen.findByText(/folio 1004/)).toBeInTheDocument()
    const [[, opciones]] = llamadas(fetchFalso, 'POST', '/reportes')
    expect(JSON.parse(opciones.body)).toEqual({
      sesion_id: 'ses-1',
      motivo: 'conducta',
      descripcion: 'Me trató mal durante la llamada',
    })
  })
})
 
describe('campana', () => {
  it('cuenta los avisos sin leer y al abrir uno lleva a su enlace', async () => {
    const fetchFalso = conSesion({
      'GET /notificaciones': () =>
        respuestaJson({
          no_leidas: 1,
          avisos: [
            {
              id: 'n-1',
              tipo: 'solicitud_aceptada',
              titulo: 'Te aceptaron la solicitud',
              mensaje: 'Rodrigo Salas acepto tu solicitud.',
              enlace: '/sesiones',
              leida: false,
              creado_en: '2026-11-03T12:00:00Z',
            },
          ],
        }),
      'POST /notificaciones/n-1/leida': () => respuestaJson({}),
      'GET /sesiones': () => respuestaJson([]),
    })
    const usuario = userEvent.setup()
    abrirEn('/')
 
    await usuario.click(await screen.findByRole('button', { name: 'Avisos, 1 sin leer' }))
    await usuario.click(screen.getByRole('button', { name: /Te aceptaron la solicitud/ }))
 
    expect(await screen.findByRole('heading', { name: 'Sesiones' })).toBeInTheDocument()
    expect(llamadas(fetchFalso, 'POST', '/notificaciones/n-1/leida')).toHaveLength(1)
  })
})
 
const REPORTE = {
  id: 'rep-1',
  folio: 1004,
  motivo: 'conducta',
  estado: 'abierto',
  congela_pago: true,
  tema_nombre: 'Álgebra',
  reportante: ANA,
  reportado: RODRIGO,
  creado_en: '2026-11-03T12:20:00Z',
}
 
const DETALLE = {
  ...REPORTE,
  descripcion: 'Me trató mal durante la llamada',
  resolucion: null,
  fecha_resolucion: null,
  sesion_id: 'ses-1',
  estado_sesion: 'terminada',
  precio_bloque: 3,
  bloques_cobrados: 1,
  fecha_conexion_ambos: '2026-11-03T12:01:00Z',
  fecha_cierre: '2026-11-03T12:16:00Z',
  motivo_cierre: 'termino el tiempo pagado',
  pago: { retenido: 3, pagado: 0, devuelto: 0 },
  sanciones_previas_reportado: 0,
  grabacion: 'disponible',
}
 
describe('soporte', () => {
  it('la bandeja muestra los reportes abiertos y el pago congelado', async () => {
    const fetchFalso = conSesion({ 'GET /soporte/reportes': () => respuestaJson([REPORTE]) }, 'soporte')
    abrirEn('/soporte')
 
    expect(await screen.findByRole('heading', { name: 'Folio 1004 · Conducta inapropiada' })).toBeInTheDocument()
    expect(screen.getByText('Pago congelado')).toBeInTheDocument()
    const [url] = fetchFalso.mock.calls.find(([u]) => u.includes('/soporte/reportes'))
    expect(new URL(url).searchParams.get('estado')).toBe('abierto')
  })
 
  it('ver la grabacion abre el enlace temporal y queda en la bitacora', async () => {
    const abrir = vi.fn()
    vi.stubGlobal('open', abrir)
    let accesos = []
    conSesion(
      {
        'GET /soporte/reportes/rep-1': () => respuestaJson(DETALLE),
        'GET /soporte/reportes/rep-1/accesos': () => respuestaJson(accesos),
        'POST /soporte/reportes/rep-1/grabacion': () => {
          accesos = [{ soporte: 'Ana López', fecha: '2026-11-03T13:00:00Z' }]
          return respuestaJson({ url: 'https://bucket/grabaciones/ses-1.mp4?firma', segundos_vigencia: 600 })
        },
      },
      'soporte',
    )
    const usuario = userEvent.setup()
    abrirEn('/soporte/rep-1')
 
    await usuario.click(await screen.findByRole('button', { name: 'Ver grabación' }))
 
    expect(abrir).toHaveBeenCalledWith('https://bucket/grabaciones/ses-1.mp4?firma', '_blank', 'noopener')
    expect(await screen.findByText(/Ana López ·/)).toBeInTheDocument()
  })
 
  it('resolver con suspension temporal manda la decision completa', async () => {
    const fetchFalso = conSesion(
      {
        'GET /soporte/reportes/rep-1': () => respuestaJson(DETALLE),
        'GET /soporte/reportes/rep-1/accesos': () => respuestaJson([]),
        'POST /soporte/reportes/rep-1/resolver': (op) =>
          respuestaJson({ ...DETALLE, estado: 'fundado', resolucion: JSON.parse(op.body).resolucion }),
      },
      'soporte',
    )
    const usuario = userEvent.setup()
    abrirEn('/soporte/rep-1')
 
    await usuario.click(await screen.findByLabelText('Fundado'))
    await usuario.type(screen.getByLabelText('Justificación'), 'La grabación confirma la conducta')
    await usuario.selectOptions(screen.getByLabelText('Sanción a Rodrigo Salas'), 'temporal')
    await usuario.clear(screen.getByLabelText('Días'))
    await usuario.type(screen.getByLabelText('Días'), '3')
    await usuario.click(screen.getByRole('button', { name: 'Resolver reporte' }))
 
    expect(await screen.findByText('Reporte resuelto. Se avisó a quien reportó.')).toBeInTheDocument()
    const [[, opciones]] = llamadas(fetchFalso, 'POST', '/resolver')
    expect(JSON.parse(opciones.body)).toEqual({
      fundado: true,
      resolucion: 'La grabación confirma la conducta',
      tipo_sancion: 'temporal',
      dias_suspension: 3,
    })
  })
 
  it('un usuario comun no entra a soporte', async () => {
    conSesion({})
    abrirEn('/soporte')
 
    expect(await screen.findByText('Esta sección es solo para el equipo de Cachai.')).toBeInTheDocument()
  })
})