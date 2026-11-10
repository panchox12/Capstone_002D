import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import App from '../App'
import { respuestaJson, simularApi, USUARIO_ANA } from '../pruebas/apiFalsa'
import { SesionProvider } from '../sesion/SesionProvider'
import { tocar } from '../sonido/sonidos'

vi.mock('../sonido/sonidos', () => ({ tocar: vi.fn(), sonidosActivos: () => true, cambiarSonidos: vi.fn() }))

function abrirEn(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <SesionProvider>
        <App />
      </SesionProvider>
    </MemoryRouter>,
  )
}

function conSesion(rol, rutas = {}) {
  localStorage.setItem('cachai_token', 'token-de-ana')
  return simularApi({ 'GET /auth/yo': () => respuestaJson({ ...USUARIO_ANA, rol }), ...rutas })
}

describe('encabezado', () => {
  it('el menú principal tiene seis secciones y las del equipo van en el menú de la cuenta', async () => {
    conSesion('soporte')
    const usuario = userEvent.setup()
    abrirEn('/temas')

    const principal = await screen.findByRole('navigation', { name: 'Principal' })
    expect(within(principal).getAllByRole('link')).toHaveLength(6)
    expect(within(principal).queryByRole('link', { name: 'Soporte' })).not.toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Menú de tu cuenta' }))
    const cuenta = screen.getByRole('navigation', { name: 'Tu cuenta' })
    expect(within(cuenta).getByRole('link', { name: 'Soporte' })).toHaveAttribute('href', '/soporte')
    expect(within(cuenta).queryByRole('link', { name: 'Administración' })).not.toBeInTheDocument()
    expect(screen.getByText(USUARIO_ANA.correo)).toBeInTheDocument()
  })

  it('el menú de la cuenta se cierra con Escape', async () => {
    conSesion('usuario')
    const usuario = userEvent.setup()
    abrirEn('/temas')

    await usuario.click(await screen.findByRole('button', { name: 'Menú de tu cuenta' }))
    expect(screen.getByRole('link', { name: 'Mi cuenta' })).toBeInTheDocument()
    await usuario.keyboard('{Escape}')

    expect(screen.queryByRole('link', { name: 'Mi cuenta' })).not.toBeInTheDocument()
  })

  it('la campana es un ícono y no un emoji', async () => {
    conSesion('usuario', { 'GET /notificaciones': () => respuestaJson({ no_leidas: 0, avisos: [] }) })
    abrirEn('/temas')

    const campana = await screen.findByRole('button', { name: 'Avisos' })

    expect(campana.querySelector('svg')).not.toBeNull()
    expect(campana.textContent).not.toContain('🔔')
  })

  it('suena cuando llega un aviso nuevo, pero no al abrir la página', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let noLeidas = 1
    conSesion('usuario', {
      'GET /notificaciones': () => respuestaJson({ no_leidas: noLeidas, avisos: [] }),
    })
    abrirEn('/temas')

    await screen.findByRole('button', { name: 'Avisos, 1 sin leer' })
    expect(tocar).not.toHaveBeenCalledWith('aviso')

    noLeidas = 2
    await vi.advanceTimersByTimeAsync(30_000)

    expect(await screen.findByRole('button', { name: 'Avisos, 2 sin leer' })).toBeInTheDocument()
    expect(tocar).toHaveBeenCalledWith('aviso')
    vi.useRealTimers()
  })
})