import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import App from '../App'
import { respuestaJson, simularApi, USUARIO_ANA } from '../pruebas/apiFalsa'
import { SesionProvider } from '../sesion/SesionProvider'

function abrirMiCuenta() {
  return render(
    <MemoryRouter initialEntries={['/mi-cuenta']}>
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
    'GET /verificacion/estado': () => respuestaJson({ verificado: true, fecha: '2026-10-01T12:00:00Z' }),
    ...rutas,
  })
}

describe('preferencias de presencia', () => {
  it('muestra los dos interruptores con lo que dice la API', async () => {
    conSesion({
      'GET /perfiles/mio/preferencias': () => respuestaJson({ mostrar_en_linea: true, acepta_diferidas: false }),
    })

    abrirMiCuenta()

    expect(await screen.findByRole('switch', { name: 'Aparecer como conectado' })).toBeChecked()
    expect(screen.getByRole('switch', { name: 'Recibir solicitudes estando fuera' })).not.toBeChecked()
  })

  it('apagar un interruptor guarda solo ese cambio', async () => {
    let actuales = { mostrar_en_linea: true, acepta_diferidas: true }
    const fetchFalso = conSesion({
      'GET /perfiles/mio/preferencias': () => respuestaJson(actuales),
      'PATCH /perfiles/mio/preferencias': (opciones) => {
        actuales = { ...actuales, ...JSON.parse(opciones.body) }
        return respuestaJson(actuales)
      },
    })
    const usuario = userEvent.setup()
    abrirMiCuenta()

    await usuario.click(await screen.findByRole('switch', { name: 'Aparecer como conectado' }))

    expect(await screen.findByRole('switch', { name: 'Aparecer como conectado' })).not.toBeChecked()
    const [, opciones] = fetchFalso.mock.calls.find(([, op]) => op.method === 'PATCH')
    expect(JSON.parse(opciones.body)).toEqual({ mostrar_en_linea: false })
  })
})