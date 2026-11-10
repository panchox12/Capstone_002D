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

const EN_CINCO_DIAS = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString()

const SALDO = {
  gratis: 7,
  pagado: 5,
  total: 12,
  retenidos: 3,
  tope_saldo_gratis: 10,
  videos_vistos_hoy: 0,
  tope_videos_por_dia: 3,
  lotes: [
    { id: 'l1', tipo_saldo: 'gratis', origen: 'entrega_semanal', cantidad_restante: 7, fecha_vencimiento: EN_CINCO_DIAS },
  ],
}

const MOVIMIENTOS = [
  {
    id: 'r1',
    fecha: '2026-11-09T14:00:00Z',
    tipo: 'consumo',
    origen: 'entrega_semanal',
    cantidad: -3,
    saldo_resultante: 12,
    tema: 'Álgebra',
    contraparte: 'Rodrigo Salas',
  },
  {
    id: 't2',
    fecha: '2026-11-08T12:00:00Z',
    tipo: 'compra',
    origen: 'compra',
    cantidad: 5,
    saldo_resultante: 15,
    tema: null,
    contraparte: null,
  },
  {
    id: 't1',
    fecha: '2026-11-02T12:00:00Z',
    tipo: 'entrega',
    origen: 'entrega_semanal',
    cantidad: 10,
    saldo_resultante: 10,
    tema: null,
    contraparte: null,
  },
]

function conSesion(movimientos = MOVIMIENTOS) {
  localStorage.setItem('cachai_token', 'token-de-ana')
  return simularApi({
    'GET /auth/yo': () => respuestaJson(USUARIO_ANA),
    'GET /tokens/saldo': () => respuestaJson(SALDO),
    'GET /tokens/movimientos': () => respuestaJson(movimientos),
  })
}

describe('historial de tokens', () => {
  it('se abre al tocar el saldo del encabezado', async () => {
    conSesion()
    const usuario = userEvent.setup()
    abrirEn('/temas')

    await usuario.click(await screen.findByRole('link', { name: '12 tokens · 3 retenidos' }))

    expect(await screen.findByRole('heading', { name: 'Tus tokens' })).toBeInTheDocument()
  })

  it('muestra cada movimiento con su signo y, si es una sesión, el tema y con quién', async () => {
    conSesion()
    abrirEn('/tokens')

    const filas = (await screen.findAllByRole('row')).slice(1)
    expect(filas).toHaveLength(3)
    expect(within(filas[0]).getByText('Pagaste una sesión')).toBeInTheDocument()
    expect(within(filas[0]).getByText('Álgebra · con Rodrigo Salas')).toBeInTheDocument()
    expect(within(filas[0]).getByText('−3')).toBeInTheDocument()
    expect(within(filas[1]).getByText('Compra de tokens')).toBeInTheDocument()
    expect(within(filas[1]).getByText('+5')).toBeInTheDocument()
    expect(within(filas[2]).getByText('Entrega semanal')).toBeInTheDocument()
  })

  it('muestra el saldo con los retenidos y lo que vence antes', async () => {
    conSesion()
    abrirEn('/tokens')

    expect(await screen.findByText('Retenidos')).toBeInTheDocument()
    expect(screen.getByText('7 tokens gratuitos')).toBeInTheDocument()
    expect(screen.getByText('en 5 días')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Recargar tokens' })).toHaveAttribute('href', '/tienda')
  })

  it('sin movimientos lo dice', async () => {
    conSesion([])
    abrirEn('/tokens')

    expect(await screen.findByText('Todavía no tienes movimientos.')).toBeInTheDocument()
  })
})