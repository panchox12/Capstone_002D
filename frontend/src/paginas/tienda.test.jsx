import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { SEGUNDOS_DE_ANUNCIO } from '../componentes/TarjetaVideo'
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

const EN_DIEZ_DIAS = new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString()

function saldo(cambios = {}) {
  return {
    gratis: 6,
    pagado: 8,
    total: 14,
    retenidos: 0,
    tope_saldo_gratis: 10,
    videos_vistos_hoy: 2,
    tope_videos_por_dia: 3,
    lotes: [
      {
        id: 'l1',
        tipo_saldo: 'gratis',
        origen: 'entrega_semanal',
        cantidad_restante: 6,
        fecha_vencimiento: EN_DIEZ_DIAS,
      },
      { id: 'l2', tipo_saldo: 'pagado', origen: 'compra', cantidad_restante: 8, fecha_vencimiento: EN_DIEZ_DIAS },
    ],
    ...cambios,
  }
}

const PAQUETES = [
  { codigo: 'basico', cantidad_tokens: 5, monto_pesos: 490, pesos_por_token: 98 },
  { codigo: 'popular', cantidad_tokens: 13, monto_pesos: 990, pesos_por_token: 76 },
  { codigo: 'volumen', cantidad_tokens: 30, monto_pesos: 1990, pesos_por_token: 66 },
]

function conSesion(rutas) {
  localStorage.setItem('cachai_token', 'token-de-ana')
  return simularApi({ 'GET /auth/yo': () => respuestaJson(USUARIO_ANA), ...rutas })
}

afterEach(() => {
  vi.useRealTimers()
})

describe('inicio con sesion', () => {
  it('muestra el saldo gratuito y el pagado por separado', async () => {
    conSesion({ 'GET /tokens/saldo': () => respuestaJson(saldo()) })

    abrirEn('/')

    expect(await screen.findByRole('heading', { name: 'Hola Ana, ¿qué duda resolvemos hoy?' })).toBeInTheDocument()
    expect(await screen.findByText('tokens gratuitos')).toBeInTheDocument()
    expect(screen.getByText('tokens pagados')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '14 tokens' })).toHaveAttribute('href', '/tienda')
  })

  it('avisa cuando hay tokens retenidos', async () => {
    conSesion({ 'GET /tokens/saldo': () => respuestaJson(saldo({ retenidos: 3, gratis: 3, total: 11 })) })

    abrirEn('/')

    expect(await screen.findByText(/Tienes 3 tokens retenidos/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '11 tokens · 3 retenidos' })).toBeInTheDocument()
  })
})

describe('tienda', () => {
  it('comprar un paquete envia su codigo y actualiza el saldo del encabezado', async () => {
    let saldoActual = saldo()
    const fetchFalso = conSesion({
      'GET /tokens/saldo': () => respuestaJson(saldoActual),
      'GET /tienda/paquetes': () => respuestaJson(PAQUETES),
      'GET /tienda/compras': () => respuestaJson([]),
      'POST /tienda/compras': () => {
        saldoActual = saldo({ pagado: 21, total: 27 })
        return respuestaJson({ id: 'c1' }, 201)
      },
    })
    const usuario = userEvent.setup()
    abrirEn('/tienda')

    await usuario.click(await screen.findByRole('button', { name: 'Comprar 13 tokens' }))

    expect(await screen.findByText('Listo: sumaste 13 tokens (pago simulado).')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: '27 tokens' })).toBeInTheDocument()
    const [, opciones] = fetchFalso.mock.calls.find(
      ([url, op]) => url.endsWith('/tienda/compras') && op.method === 'POST',
    )
    expect(JSON.parse(opciones.body)).toEqual({ paquete: 'popular' })
  })

  it('el historial muestra cuanto queda de cada compra', async () => {
    conSesion({
      'GET /tokens/saldo': () => respuestaJson(saldo()),
      'GET /tienda/paquetes': () => respuestaJson(PAQUETES),
      'GET /tienda/compras': () =>
        respuestaJson([
          compra({ id: 'a', tokens_restantes: 5 }),
          compra({ id: 'b', tokens_restantes: 0 }),
          compra({ id: 'c', tokens_restantes: 2, vencida: true }),
        ]),
    })

    abrirEn('/tienda')

    expect(await screen.findByText('5 restantes')).toBeInTheDocument()
    expect(screen.getByText('Consumido')).toBeInTheDocument()
    expect(screen.getByText('2 vencidos')).toBeInTheDocument()
  })
})

function compra(cambios) {
  return {
    paquete: 'popular',
    cantidad_tokens: 13,
    monto_pesos: 990,
    estado: 'pagada',
    fecha: '2026-10-01T15:00:00Z',
    fecha_vencimiento: '2026-10-31T15:00:00Z',
    vencida: false,
    ...cambios,
  }
}

describe('videos', () => {
  it('al terminar la cuenta regresiva registra el video y actualiza el saldo', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let saldoActual = saldo()
    const fetchFalso = conSesion({
      'GET /tokens/saldo': () => respuestaJson(saldoActual),
      'POST /tokens/videos': () => {
        saldoActual = saldo({ gratis: 7, total: 15, videos_vistos_hoy: 3 })
        return respuestaJson({ tokens_otorgados: 1, videos_vistos_hoy: 3, tope_videos_por_dia: 3 }, 201)
      },
    })
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    abrirEn('/')

    await usuario.click(await screen.findByRole('button', { name: `Ver video · ${SEGUNDOS_DE_ANUNCIO} seg` }))
    expect(fetchFalso.mock.calls.some(([url]) => url.endsWith('/tokens/videos'))).toBe(false)

    for (let segundo = 0; segundo < SEGUNDOS_DE_ANUNCIO; segundo++) {
      await act(() => vi.advanceTimersByTime(1000))
    }

    expect(await screen.findByText('Sumaste 1 token gratuito.')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('link', { name: '15 tokens' })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Vuelve mañana por más videos' })).toBeDisabled()
  })

  it('con el saldo gratuito lleno no deja ver videos', async () => {
    conSesion({ 'GET /tokens/saldo': () => respuestaJson(saldo({ gratis: 10, total: 18 })) })

    abrirEn('/')

    expect(await screen.findByRole('button', { name: 'Tu saldo gratuito está completo' })).toBeDisabled()
  })
})