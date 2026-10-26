import { render, screen, waitFor } from '@testing-library/react'
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

function cuerpoDe(fetchFalso, ruta) {
  const [, opciones] = fetchFalso.mock.calls.find(([url]) => url.endsWith(ruta))
  return JSON.parse(opciones.body)
}

async function llenarRegistro(usuario) {
  await usuario.type(screen.getByLabelText('Nombre visible'), 'Ana López')
  await usuario.type(screen.getByLabelText('Correo'), 'ana@duoc.cl')
  await usuario.type(screen.getByLabelText('Contraseña'), 'clave12345')
  await usuario.click(screen.getByRole('checkbox', { name: 'Acepto los términos y condiciones de Cachai' }))
  await usuario.click(screen.getByRole('checkbox', { name: 'Autorizo que mis sesiones se graben en audio y video' }))
}

describe('crear cuenta', () => {
  it('envia los dos consentimientos por separado y pide revisar el correo', async () => {
    const fetchFalso = simularApi({ 'POST /auth/registro': () => respuestaJson({ id: 'nuevo' }, 201) })
    const usuario = userEvent.setup()
    abrirEn('/crear-cuenta')

    await llenarRegistro(usuario)
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('heading', { name: 'Revisa tu correo' })).toBeInTheDocument()
    expect(cuerpoDe(fetchFalso, '/auth/registro')).toEqual({
      nombre_visible: 'Ana López',
      correo: 'ana@duoc.cl',
      contrasena: 'clave12345',
      acepta_terminos: true,
      consentimiento_grabacion: true,
    })
  })

  it('sin autorizar la grabacion no se puede enviar', async () => {
    simularApi({})
    const usuario = userEvent.setup()
    abrirEn('/crear-cuenta')

    await usuario.type(screen.getByLabelText('Nombre visible'), 'Ana López')
    await usuario.type(screen.getByLabelText('Correo'), 'ana@duoc.cl')
    await usuario.type(screen.getByLabelText('Contraseña'), 'clave12345')
    await usuario.click(screen.getByRole('checkbox', { name: 'Acepto los términos y condiciones de Cachai' }))

    expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeDisabled()
  })

  it('avisa lo que le falta a la contraseña mientras se escribe', async () => {
    simularApi({})
    const usuario = userEvent.setup()
    abrirEn('/crear-cuenta')

    await usuario.type(screen.getByLabelText('Contraseña'), 'corta')

    expect(screen.getByText('Le falta: al menos 10 caracteres, un número.')).toBeInTheDocument()
  })

  it('un correo ya registrado muestra el error', async () => {
    simularApi({
      'POST /auth/registro': () => respuestaJson({ detail: 'Ya existe una cuenta con ese correo' }, 409),
    })
    const usuario = userEvent.setup()
    abrirEn('/crear-cuenta')

    await llenarRegistro(usuario)
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe una cuenta con ese correo.')
  })
})

describe('confirmar correo', () => {
  it('con un enlace valido muestra la cuenta activa', async () => {
    simularApi({
      'GET /auth/confirmar/token-valido': () =>
        respuestaJson({ mensaje: 'Cuenta confirmada. Ya puedes iniciar sesion' }),
    })

    abrirEn('/confirmar/token-valido')

    expect(await screen.findByRole('heading', { name: 'Tu cuenta está activa' })).toBeInTheDocument()
  })

  it('con un enlace vencido explica el problema', async () => {
    simularApi({
      'GET /auth/confirmar/token-viejo': () =>
        respuestaJson({ detail: 'El enlace de confirmacion vencio. Solicita uno nuevo' }, 400),
    })

    abrirEn('/confirmar/token-viejo')

    expect(await screen.findByRole('alert')).toHaveTextContent('El enlace de confirmacion vencio')
  })
})

describe('verificar identidad', () => {
  const PNG = new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], 'foto.png', { type: 'image/png' })

  function conSesion(rutasExtra) {
    localStorage.setItem('cachai_token', 'token-de-ana')
    return simularApi({ 'GET /auth/yo': () => respuestaJson(USUARIO_ANA), ...rutasExtra })
  }

  it('si ya esta verificada lo dice y no muestra el formulario', async () => {
    conSesion({
      'GET /verificacion/estado': () => respuestaJson({ verificado: true, fecha: '2026-10-01T12:00:00Z' }),
    })

    abrirEn('/verificar')

    expect(await screen.findByRole('heading', { name: 'Tu identidad está verificada' })).toBeInTheDocument()
  })

  it('envia las tres fotos en base64 sin el prefijo', async () => {
    const fetchFalso = conSesion({
      'GET /verificacion/estado': () => respuestaJson({ verificado: false, fecha: null }),
      'POST /verificacion': () =>
        respuestaJson({ resultado: 'aprobado', nivel_confianza: 92.5, fecha: '2026-10-14T12:00:00Z' }, 201),
    })
    const usuario = userEvent.setup()
    abrirEn('/verificar')

    await usuario.upload(await screen.findByLabelText('Frente de tu cédula'), PNG)
    await usuario.upload(screen.getByLabelText('Reverso de tu cédula'), PNG)
    await usuario.upload(screen.getByLabelText('Una selfie'), PNG)
    await usuario.click(screen.getByRole('checkbox', { name: /datos biométricos/ }))
    await usuario.click(screen.getByRole('button', { name: 'Verificar mi identidad' }))

    expect(await screen.findByRole('heading', { name: 'Tu identidad está verificada' })).toBeInTheDocument()
    const cuerpo = cuerpoDe(fetchFalso, '/verificacion')
    expect(cuerpo.documento_frontal).toBe('iVBORw==')
    expect(cuerpo.consentimiento_biometrico).toBe(true)
  })

  it('rechaza un archivo que no es JPG ni PNG antes de enviarlo', async () => {
    conSesion({ 'GET /verificacion/estado': () => respuestaJson({ verificado: false, fecha: null }) })
    const usuario = userEvent.setup({ applyAccept: false })
    abrirEn('/verificar')

    const pdf = new File(['%PDF'], 'cedula.pdf', { type: 'application/pdf' })
    await usuario.upload(await screen.findByLabelText('Frente de tu cédula'), pdf)

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Sube una foto en formato JPG o PNG.'))
  })
})
