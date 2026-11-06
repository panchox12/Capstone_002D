import { render, screen } from '@testing-library/react'
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
 
function conRol(rol, rutas = {}) {
  localStorage.setItem('cachai_token', 'token-de-ana')
  return simularApi({
    'GET /auth/yo': () => respuestaJson({ ...USUARIO_ANA, rol }),
    'GET /tokens/saldo': () => respuestaJson({ gratis: 7, pagado: 0, total: 7, retenidos: 0, lotes: [] }),
    ...rutas,
  })
}
 
const INDICADORES = {
  dias_ventana: 30,
  masa_circulante: 120,
  tokens_retenidos: 9,
  tokens_entregados: 200,
  tokens_consumidos: 60,
  tokens_vencidos: 20,
  velocidad: 0.5,
  tasa_caducidad: 0.1,
  cobertura_gratuita: 0.75,
  conversion: 0.25,
  usuarios_activos: 40,
  sesiones_terminadas: 18,
}
 
const PARAMETROS = [
  { nombre: 'tokens_gratis_semanales', valor: '10', descripcion: 'Tokens gratis que se entregan cada semana', actualizado_en: '2026-11-01T00:00:00Z' },
]
 
describe('panel del administrador', () => {
  it('muestra los indicadores con formato', async () => {
    conRol('administrador', {
      'GET /admin/indicadores': () => respuestaJson(INDICADORES),
      'GET /admin/parametros': () => respuestaJson(PARAMETROS),
    })
    abrirEn('/admin')
 
    expect(await screen.findByText('120')).toBeInTheDocument()
    // Segun el navegador, Intl pone o no un espacio antes del signo.
    expect(screen.getByText(/^75\s?%$/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Administración' })).toBeInTheDocument()
  })
 
  it('guarda un parametro cambiado', async () => {
    const fetchFalso = conRol('administrador', {
      'GET /admin/indicadores': () => respuestaJson(INDICADORES),
      'GET /admin/parametros': () => respuestaJson(PARAMETROS),
      'PUT /admin/parametros/tokens_gratis_semanales': (op) =>
        respuestaJson({ ...PARAMETROS[0], valor: String(JSON.parse(op.body).valor) }),
    })
    const usuario = userEvent.setup()
    abrirEn('/admin')
 
    const campo = await screen.findByLabelText(/Tokens gratis que se entregan cada semana/)
    await usuario.clear(campo)
    await usuario.type(campo, '12')
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }))
 
    expect(await screen.findByText('Se guardó tokens_gratis_semanales: ahora vale 12.')).toBeInTheDocument()
    const [, opciones] = fetchFalso.mock.calls.find(([, op]) => op.method === 'PUT')
    expect(JSON.parse(opciones.body)).toEqual({ valor: 12 })
  })
 
  it('un usuario comun no ve el panel ni el enlace', async () => {
    conRol('usuario')
    abrirEn('/admin')
 
    expect(await screen.findByText('Esta sección es solo para el equipo de Cachai.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Administración' })).not.toBeInTheDocument()
  })
})