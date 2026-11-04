import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import App from '../App'
import { respuestaJson, simularApi, USUARIO_ANA } from '../pruebas/apiFalsa'
import { SesionProvider } from '../sesion/SesionProvider'

// La videollamada real necesita WebRTC: en las pruebas se reemplaza por un marcador.
vi.mock('../sala/VideoLlamada', () => ({
  VideoLlamada: ({ permiso }) => <div data-testid="videollamada">{permiso.nombre_sala}</div>,
}))

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
    'GET /tokens/saldo': () => respuestaJson({ gratis: 7, pagado: 0, total: 7, retenidos: 3, lotes: [] }),
    ...rutas,
  })
}

const ANA = { id: USUARIO_ANA.id, nombre_visible: 'Ana López' }
const RODRIGO = { id: 'tutor-1', nombre_visible: 'Rodrigo Salas' }

function sesion(cambios = {}) {
  return {
    id: 'ses-1',
    solicitud_id: 'sol-1',
    estado: 'esperando',
    tema_nombre: 'Álgebra',
    precio_bloque: 3,
    aprendiz: ANA,
    tutor: RODRIGO,
    fecha_apertura_sala: '2026-11-03T12:00:00Z',
    fecha_limite_conexion: '2026-11-03T12:05:00Z',
    fecha_conexion_ambos: null,
    fecha_cierre: null,
    bloques_cobrados: 0,
    motivo_cierre: null,
    segundos_para_conectarse: 280,
    segundos_restantes_bloque: 0,
    extension_propuesta_por: null,
    pausa_activa: false,
    usuario_caido_id: null,
    segundos_para_reconectar: 0,
    pausas_usadas: 0,
    pausas_maximas: 3,
    ...cambios,
  }
}

describe('historial de sesiones', () => {
  it('lista las sesiones con la otra persona y su estado', async () => {
    conSesion({
      'GET /sesiones': () =>
        respuestaJson([sesion({ estado: 'terminada', bloques_cobrados: 2 }), sesion({ id: 'ses-2', tutor: ANA, aprendiz: RODRIGO })]),
    })
    abrirEn('/sesiones')

    expect(await screen.findByRole('heading', { name: 'Álgebra · con Rodrigo Salas' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Álgebra · ayudaste a Rodrigo Salas' })).toBeInTheDocument()
    expect(screen.getByText('Terminada')).toBeInTheDocument()
    expect(screen.getByText(/2 bloques/)).toBeInTheDocument()
  })

  it('avisa cuando todavia no hay sesiones', async () => {
    conSesion({ 'GET /sesiones': () => respuestaJson([]) })
    abrirEn('/sesiones')

    expect(await screen.findByText(/Todavía no tienes sesiones/)).toBeInTheDocument()
  })
})

describe('sala', () => {
  it('mientras esperan muestra el plazo y el aviso de grabacion', async () => {
    conSesion({ 'GET /sesiones/ses-1': () => respuestaJson(sesion()) })
    abrirEn('/sesiones/ses-1')

    expect(await screen.findByText('4:40')).toBeInTheDocument()
    expect(screen.getByText(/Esta sesión se graba/)).toBeInTheDocument()
    expect(screen.getByText('Te ayuda Rodrigo Salas')).toBeInTheDocument()
  })

  it('entrar pide el permiso y abre la videollamada', async () => {
    const fetchFalso = conSesion({
      'GET /sesiones/ses-1': () => respuestaJson(sesion()),
      'POST /sesiones/ses-1/entrar': () =>
        respuestaJson({ url: 'wss://cachai.livekit.cloud', token: 'permiso', nombre_sala: 'cachai-ses-1' }),
    })
    const usuario = userEvent.setup()
    abrirEn('/sesiones/ses-1')

    await usuario.click(await screen.findByRole('button', { name: 'Entrar a la sala' }))

    expect(await screen.findByTestId('videollamada')).toHaveTextContent('cachai-ses-1')
    expect(fetchFalso.mock.calls.some(([url, op]) => url.endsWith('/entrar') && op.method === 'POST')).toBe(true)
  })

  it('en curso muestra el tiempo pagado y el indicador de grabacion', async () => {
    conSesion({
      'GET /sesiones/ses-1': () =>
        respuestaJson(sesion({ estado: 'en_curso', bloques_cobrados: 1, segundos_restantes_bloque: 905 })),
    })
    abrirEn('/sesiones/ses-1')

    expect(await screen.findByText('15:05')).toBeInTheDocument()
    expect(screen.getByText('● Grabando')).toBeInTheDocument()
  })

  it('si la otra persona se cae avisa cuanto tiene para volver', async () => {
    conSesion({
      'GET /sesiones/ses-1': () =>
        respuestaJson(
          sesion({
            estado: 'en_curso',
            bloques_cobrados: 1,
            segundos_restantes_bloque: 600,
            pausa_activa: true,
            usuario_caido_id: RODRIGO.id,
            segundos_para_reconectar: 75,
            pausas_usadas: 1,
          }),
        ),
    })
    abrirEn('/sesiones/ses-1')

    expect(await screen.findByText(/Rodrigo Salas perdió la conexión/)).toBeInTheDocument()
    expect(screen.getByText(/Pausas usadas: 1 de 3/)).toBeInTheDocument()
  })

  it('terminada muestra el resumen sin boton para entrar', async () => {
    conSesion({
      'GET /sesiones/ses-1': () =>
        respuestaJson(sesion({ estado: 'terminada', bloques_cobrados: 2, motivo_cierre: 'termino el tiempo pagado' })),
    })
    abrirEn('/sesiones/ses-1')

    expect(await screen.findByText('Motivo de cierre: termino el tiempo pagado.')).toBeInTheDocument()
    expect(screen.getByText(/2 bloques cobrados · 6 tokens/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Entrar a la sala' })).not.toBeInTheDocument()
  })

  it('una sesion ajena muestra el error de la API', async () => {
    conSesion({ 'GET /sesiones/ses-9': () => respuestaJson({ detail: 'Sesion no encontrada' }, 404) })
    abrirEn('/sesiones/ses-9')

    expect(await screen.findByRole('alert')).toHaveTextContent('Sesion no encontrada')
  })
})