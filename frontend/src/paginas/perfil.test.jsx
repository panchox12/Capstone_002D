import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import App from '../App'
import { respuestaJson, simularApi, USUARIO_ANA } from '../pruebas/apiFalsa'
import { SesionProvider } from '../sesion/SesionProvider'
 
const TUTOR_ID = '0b6f3c1e-0000-4000-8000-000000000002'
 
const CATALOGO = [
  {
    id: 1,
    nombre: 'Ciencias exactas',
    nivel: 1,
    hijos: [
      {
        id: 2,
        nombre: 'Matemáticas',
        nivel: 2,
        hijos: [
          { id: 3, nombre: 'Álgebra', nivel: 3, hijos: [] },
          { id: 4, nombre: 'Cálculo', nivel: 3, hijos: [] },
        ],
      },
    ],
  },
]
 
function habilidad(cambios = {}) {
  return { id: 'hab-1', tema_id: 3, tema_nombre: 'Álgebra', precio_por_bloque: 3, estado: 'publicada', ...cambios }
}
 
function perfil(cambios = {}) {
  return {
    usuario_id: TUTOR_ID,
    nombre_visible: 'Rodrigo Salas',
    biografia: 'Profesor de matemáticas',
    enlace_personalizado: 'rodrigo',
    url_perfil: 'http://localhost:5173/u/rodrigo',
    reputacion_promedio: '4.70',
    total_evaluaciones: 3,
    consultas_completadas: 3,
    habilidades: [habilidad()],
    en_linea: true,
    ...cambios,
  }
}
 
function abrirEn(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <SesionProvider>
        <App />
      </SesionProvider>
    </MemoryRouter>,
  )
}
 
function conSesion(rutas, verificado = true) {
  localStorage.setItem('cachai_token', 'token-de-ana')
  return simularApi({
    'GET /auth/yo': () => respuestaJson(USUARIO_ANA),
    'GET /verificacion/estado': () => respuestaJson({ verificado }),
    'GET /perfiles/mio/preferencias': () => respuestaJson({ mostrar_en_linea: true, acepta_diferidas: true }),
    'GET /bloqueos': () => respuestaJson([]),
    'GET /temas': () => respuestaJson(CATALOGO),
    [`GET /perfiles/${USUARIO_ANA.id}`]: () =>
      respuestaJson(perfil({ usuario_id: USUARIO_ANA.id, biografia: null, enlace_personalizado: null, habilidades: [] })),
    ...rutas,
  })
}
 
function cuerpoDe(fetchFalso, metodo, final) {
  const [, opciones] = fetchFalso.mock.calls.find(([url, op]) => op.method === metodo && url.endsWith(final))
  return JSON.parse(opciones.body)
}
 
afterEach(() => localStorage.clear())
 
describe('mis habilidades', () => {
  it('publica una habilidad con el tema y el precio elegidos', async () => {
    const fetchFalso = conSesion({
      'GET /habilidades/mias': () => respuestaJson([]),
      'POST /habilidades': () => respuestaJson(habilidad({ precio_por_bloque: 2 }), 201),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    expect(await screen.findByText('Todavía no ofreces ninguna habilidad.')).toBeInTheDocument()
    await usuario.selectOptions(await screen.findByLabelText('Tema'), 'Álgebra')
    const campoPrecio = screen.getByLabelText(/Precio por bloque de 15 minutos/)
    await usuario.clear(campoPrecio)
    await usuario.type(campoPrecio, '2')
    await usuario.click(screen.getByRole('button', { name: 'Publicar habilidad' }))
 
    expect(await screen.findByText('2 tokens por bloque')).toBeInTheDocument()
    expect(cuerpoDe(fetchFalso, 'POST', '/habilidades')).toEqual({ tema_id: 3, precio_por_bloque: 2 })
  })
 
  it('no deja elegir un tema que ya se ofrece', async () => {
    conSesion({ 'GET /habilidades/mias': () => respuestaJson([habilidad()]) })
    abrirEn('/mi-cuenta')
 
    const selector = await screen.findByLabelText('Tema')
 
    expect(within(selector).getByRole('option', { name: 'Álgebra' })).toBeDisabled()
    expect(within(selector).getByRole('option', { name: 'Cálculo' })).toBeEnabled()
  })
 
  it('pausa una habilidad y la puede volver a publicar', async () => {
    const fetchFalso = conSesion({
      'GET /habilidades/mias': () => respuestaJson([habilidad()]),
      'PATCH /habilidades/hab-1': (opciones) => respuestaJson(habilidad(JSON.parse(opciones.body))),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    await usuario.click(await screen.findByRole('button', { name: 'Pausar Álgebra' }))
 
    expect(await screen.findByText('Pausada')).toBeInTheDocument()
    expect(cuerpoDe(fetchFalso, 'PATCH', '/habilidades/hab-1')).toEqual({ estado: 'pausada' })
    expect(screen.getByRole('button', { name: 'Publicar Álgebra' })).toBeInTheDocument()
  })
 
  it('cambia el precio de una habilidad', async () => {
    const fetchFalso = conSesion({
      'GET /habilidades/mias': () => respuestaJson([habilidad()]),
      'PATCH /habilidades/hab-1': (opciones) => respuestaJson(habilidad(JSON.parse(opciones.body))),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    await usuario.click(await screen.findByRole('button', { name: 'Cambiar precio de Álgebra' }))
    const campo = screen.getByLabelText('Nuevo precio por bloque')
    await usuario.clear(campo)
    await usuario.type(campo, '5')
    await usuario.click(screen.getByRole('button', { name: 'Guardar precio' }))
 
    expect(await screen.findByText('5 tokens por bloque')).toBeInTheDocument()
    expect(cuerpoDe(fetchFalso, 'PATCH', '/habilidades/hab-1')).toEqual({ precio_por_bloque: 5 })
  })
 
  it('muestra el error de la API al publicar', async () => {
    conSesion({
      'GET /habilidades/mias': () => respuestaJson([]),
      'POST /habilidades': () => respuestaJson({ detail: 'Ya ofreces este tema' }, 409),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    await usuario.selectOptions(await screen.findByLabelText('Tema'), 'Álgebra')
    await usuario.click(screen.getByRole('button', { name: 'Publicar habilidad' }))
 
    expect(await screen.findByText('Ya ofreces este tema')).toBeInTheDocument()
  })
 
  it('sin identidad verificada no ofrece publicar', async () => {
    conSesion({ 'GET /habilidades/mias': () => respuestaJson([]) }, false)
    abrirEn('/mi-cuenta')
 
    expect(await screen.findByText('Para enseñar necesitas verificar tu identidad.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publicar habilidad' })).not.toBeInTheDocument()
  })
})
 
describe('mi perfil', () => {
  it('guarda la biografia y el alias', async () => {
    const fetchFalso = conSesion({
      'GET /habilidades/mias': () => respuestaJson([]),
      'PATCH /perfiles/mio': (opciones) =>
        respuestaJson(perfil({ usuario_id: USUARIO_ANA.id, ...JSON.parse(opciones.body) })),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    await usuario.type(await screen.findByLabelText('Cómo te presentas'), 'Estudio pedagogía')
    await usuario.type(screen.getByLabelText('Enlace de tu perfil'), 'Ana-Lopez')
    await usuario.click(screen.getByRole('button', { name: 'Guardar perfil' }))
 
    expect(await screen.findByText('Guardamos tu perfil.')).toBeInTheDocument()
    expect(cuerpoDe(fetchFalso, 'PATCH', '/perfiles/mio')).toEqual({
      biografia: 'Estudio pedagogía',
      enlace_personalizado: 'ana-lopez',
    })
    expect(screen.getByRole('link', { name: 'Ver mi perfil público' })).toHaveAttribute('href', '/u/ana-lopez')
  })
 
  it('sin alias no lo envia, porque la API no permite dejarlo vacio', async () => {
    const fetchFalso = conSesion({
      'GET /habilidades/mias': () => respuestaJson([]),
      'PATCH /perfiles/mio': () => respuestaJson(perfil({ usuario_id: USUARIO_ANA.id, enlace_personalizado: null })),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    await screen.findByLabelText('Cómo te presentas')
    await usuario.click(screen.getByRole('button', { name: 'Guardar perfil' }))
 
    await screen.findByText('Guardamos tu perfil.')
    expect(cuerpoDe(fetchFalso, 'PATCH', '/perfiles/mio')).toEqual({ biografia: '' })
  })
 
  it('muestra el aviso si el alias ya esta tomado', async () => {
    conSesion({
      'GET /habilidades/mias': () => respuestaJson([]),
      'PATCH /perfiles/mio': () => respuestaJson({ detail: 'Ese enlace ya esta tomado por otro usuario' }, 409),
    })
    const usuario = userEvent.setup()
    abrirEn('/mi-cuenta')
 
    await usuario.type(await screen.findByLabelText('Enlace de tu perfil'), 'rodrigo')
    await usuario.click(screen.getByRole('button', { name: 'Guardar perfil' }))
 
    expect(await screen.findByText('Ese enlace ya esta tomado por otro usuario')).toBeInTheDocument()
  })
})
 
describe('perfil publico', () => {
  it('un visitante ve al tutor y se le pide ingresar para pedir ayuda', async () => {
    simularApi({ 'GET /perfiles/rodrigo': () => respuestaJson(perfil()) })
 
    abrirEn('/u/rodrigo')
 
    expect(await screen.findByRole('heading', { name: 'Rodrigo Salas' })).toBeInTheDocument()
    expect(screen.getByText('Profesor de matemáticas')).toBeInTheDocument()
    expect(screen.getByText('En línea')).toBeInTheDocument()
    expect(screen.getByText('Álgebra')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ingresa para pedir ayuda' })).toHaveAttribute('href', '/ingresar')
    expect(screen.queryByRole('button', { name: 'Pedir ayuda con Álgebra' })).not.toBeInTheDocument()
  })
 
  it('con menos de 5 valoraciones dice usuario nuevo y no muestra el promedio', async () => {
    simularApi({ 'GET /perfiles/rodrigo': () => respuestaJson(perfil({ total_evaluaciones: 4 })) })
 
    abrirEn('/u/rodrigo')
 
    expect(await screen.findByText('Usuario nuevo')).toBeInTheDocument()
    expect(screen.queryByText(/4,7/)).not.toBeInTheDocument()
  })
 
  it('desde 5 valoraciones muestra el promedio', async () => {
    simularApi({ 'GET /perfiles/rodrigo': () => respuestaJson(perfil({ total_evaluaciones: 5 })) })
 
    abrirEn('/u/rodrigo')
 
    expect(await screen.findByText('★ 4,7 · 5 sesiones valoradas')).toBeInTheDocument()
  })
 
  it('pedir ayuda desde el perfil envia la solicitud y lleva a Solicitudes', async () => {
    const fetchFalso = conSesion({
      'GET /perfiles/rodrigo': () => respuestaJson(perfil()),
      'POST /solicitudes': () => respuestaJson({ id: 'sol-1', modalidad: 'en_vivo' }, 201),
      'GET /solicitudes/recibidas': () => respuestaJson([]),
      'GET /solicitudes/enviadas': () => respuestaJson([]),
    })
    const usuario = userEvent.setup()
    abrirEn('/u/rodrigo')
 
    await usuario.click(await screen.findByRole('button', { name: 'Pedir ayuda con Álgebra' }))
    await usuario.type(screen.getByLabelText('Mensaje para Rodrigo Salas'), 'No entiendo factorizar')
    await usuario.click(screen.getByRole('button', { name: 'Enviar solicitud' }))
 
    expect(await screen.findByRole('heading', { name: 'Solicitudes' })).toBeInTheDocument()
    expect(screen.getByText('Le enviaste tu duda a Rodrigo Salas. Tiene 5 minutos para responder.')).toBeInTheDocument()
    expect(cuerpoDe(fetchFalso, 'POST', '/solicitudes')).toEqual({
      habilidad_id: 'hab-1',
      mensaje: 'No entiendo factorizar',
    })
  })
 
  it('en el perfil propio ofrece editar y no pedir ayuda', async () => {
    conSesion({ 'GET /perfiles/ana': () => respuestaJson(perfil({ usuario_id: USUARIO_ANA.id })) })
 
    abrirEn('/u/ana')
 
    expect(await screen.findByRole('link', { name: 'Editar mi perfil' })).toHaveAttribute('href', '/mi-cuenta')
    expect(screen.queryByRole('button', { name: 'Pedir ayuda con Álgebra' })).not.toBeInTheDocument()
  })
 
  it('si no existe lo dice', async () => {
    simularApi({ 'GET /perfiles/nadie': () => respuestaJson({ detail: 'Perfil no encontrado' }, 404) })
 
    abrirEn('/u/nadie')
 
    expect(await screen.findByText('Perfil no encontrado')).toBeInTheDocument()
  })
 
  it('desde el buscador se llega al perfil del tutor', async () => {
    conSesion({
      'GET /buscar': () =>
        respuestaJson({
          modo: 'semantico',
          resultados: [
            {
              habilidad_id: 'hab-1',
              tema_id: 3,
              tema_nombre: 'Álgebra',
              ruta: 'Ciencias exactas > Matemáticas',
              puntaje: 0.6,
              precio_por_bloque: 3,
              tutor_id: TUTOR_ID,
              tutor_nombre: 'Rodrigo Salas',
              reputacion_promedio: null,
              total_evaluaciones: 0,
              en_linea: true,
            },
          ],
        }),
    })
    const usuario = userEvent.setup()
    abrirEn('/buscar')
 
    await usuario.type(await screen.findByLabelText('Tu duda'), 'no entiendo factorizar')
    await usuario.click(screen.getByRole('button', { name: 'Buscar' }))
 
    expect(await screen.findByRole('link', { name: 'Rodrigo Salas' })).toHaveAttribute('href', `/u/${TUTOR_ID}`)
  })
})