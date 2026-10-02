import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import App from './App'
import { respuestaJson, simularApi, USUARIO_ANA } from './pruebas/apiFalsa'
import { SesionProvider } from './sesion/SesionProvider'

function abrirEn(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <SesionProvider>
        <App />
      </SesionProvider>
    </MemoryRouter>,
  )
}

describe('sesion y rutas privadas', () => {
  it('sin sesion, Mi cuenta manda a la pagina de ingreso', async () => {
    simularApi({})

    abrirEn('/mi-cuenta')

    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
  })

  it('iniciar sesion guarda el token y lleva a la pagina que se pidio', async () => {
    const fetchFalso = simularApi({
      'POST /auth/login': () => respuestaJson({ access_token: 'token-de-ana', token_type: 'bearer' }),
      'GET /auth/yo': () => respuestaJson(USUARIO_ANA),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')

    await usuario.type(await screen.findByLabelText('Correo'), 'ana@duoc.cl')
    await usuario.type(screen.getByLabelText('Contraseña'), 'clave12345')
    await usuario.click(screen.getByRole('button', { name: 'Ingresar' }))

    expect(await screen.findByRole('heading', { name: 'Hola, Ana López' })).toBeInTheDocument()
    expect(localStorage.getItem('cachai_token')).toBe('token-de-ana')
    const [, opcionesYo] = fetchFalso.mock.calls.find(([url]) => url.endsWith('/auth/yo'))
    expect(opcionesYo.headers.Authorization).toBe('Bearer token-de-ana')
  })

  it('una contraseña incorrecta muestra el error y no guarda nada', async () => {
    simularApi({
      'POST /auth/login': () => respuestaJson({ detail: 'Correo o contrasena incorrectos' }, 401),
    })
    const usuario = userEvent.setup()
    abrirEn('/ingresar')

    await usuario.type(screen.getByLabelText('Correo'), 'ana@duoc.cl')
    await usuario.type(screen.getByLabelText('Contraseña'), 'equivocada1')
    await usuario.click(screen.getByRole('button', { name: 'Ingresar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Correo o contraseña incorrectos.')
    expect(localStorage.getItem('cachai_token')).toBeNull()
  })

  it('la sesion sobrevive a recargar la pagina', async () => {
    localStorage.setItem('cachai_token', 'token-guardado')
    simularApi({ 'GET /auth/yo': () => respuestaJson(USUARIO_ANA) })

    abrirEn('/mi-cuenta')

    expect(await screen.findByRole('heading', { name: 'Hola, Ana López' })).toBeInTheDocument()
  })

  it('un token vencido cierra la sesion y vuelve al ingreso', async () => {
    localStorage.setItem('cachai_token', 'token-vencido')
    simularApi({ 'GET /auth/yo': () => respuestaJson({ detail: 'No se pudo validar la credencial' }, 401) })

    abrirEn('/mi-cuenta')

    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
    expect(localStorage.getItem('cachai_token')).toBeNull()
  })

  it('cerrar sesion borra el token y muestra de nuevo Ingresar', async () => {
    localStorage.setItem('cachai_token', 'token-guardado')
    simularApi({ 'GET /auth/yo': () => respuestaJson(USUARIO_ANA) })
    const usuario = userEvent.setup()
    abrirEn('/')

    await usuario.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))

    const menu = screen.getByRole('navigation', { name: 'Principal' })
    expect(within(menu).getByRole('link', { name: 'Ingresar' })).toBeInTheDocument()
    expect(localStorage.getItem('cachai_token')).toBeNull()
  })
})

describe('catalogo', () => {
  it('muestra los temas de la API en sus tres niveles', async () => {
    simularApi({
      'GET /temas': () =>
        respuestaJson([
          {
            id: 1, nombre: 'Ciencias exactas', nivel: 1, descripcion: null,
            hijos: [{ id: 2, nombre: 'Matemáticas', nivel: 2, descripcion: null,
              hijos: [{ id: 3, nombre: 'Álgebra', nivel: 3, descripcion: null, hijos: [] }] }],
          },
        ]),
    })

    abrirEn('/temas')

    expect(await screen.findByRole('heading', { name: 'Ciencias exactas' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Matemáticas' })).toBeInTheDocument()
    expect(screen.getByText('Álgebra')).toBeInTheDocument()
  })

  it('si la API no responde, lo dice en vez de quedarse cargando', async () => {
    simularApi({ 'GET /temas': () => Promise.reject(new TypeError('Failed to fetch')) })

    abrirEn('/temas')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con la API')
  })
})

describe('navegacion', () => {
  it('una direccion que no existe muestra la pagina de error', async () => {
    simularApi({})

    abrirEn('/no-existe')

    expect(await screen.findByRole('heading', { name: 'Esta página no existe' })).toBeInTheDocument()
  })
})
