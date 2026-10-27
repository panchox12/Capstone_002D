import { useEffect, useState } from 'react'
import { obtenerEstadoVerificacion, verificarIdentidad } from '../api/verificacion'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton, BotonEnlace } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'
import { claseBoton } from '../componentes/ui/clases'

const TIPOS_PERMITIDOS = ['image/jpeg', 'image/png']
const TAMANO_MAXIMO = 5 * 1024 * 1024

const FOTOS = [
  { clave: 'documentoFrontal', titulo: 'Frente de tu cédula', ayuda: 'Que se lea tu RUN y se vea tu foto.' },
  { clave: 'documentoReverso', titulo: 'Reverso de tu cédula', ayuda: 'Completo, sin cortar los bordes.' },
  { clave: 'rostro', titulo: 'Una selfie', ayuda: 'De frente, con buena luz y sin lentes de sol.', camara: 'user' },
]

/** Lee un archivo como "data:image/png;base64,....". Sirve para la vista previa y para enviarlo. */
function leerComoDataUrl(archivo) {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader()
    lector.onload = () => resolver(String(lector.result))
    lector.onerror = () => rechazar(lector.error)
    lector.readAsDataURL(archivo)
  })
}

function fechaLegible(iso) {
  return new Date(iso).toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function Verificar() {
  const { token } = useSesion()
  const [estado, setEstado] = useState(null)
  const [fotos, setFotos] = useState({})
  const [consentimiento, setConsentimiento] = useState(false)
  const [error, setError] = useState(null)
  const [rechazada, setRechazada] = useState(false)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    let vigente = true
    obtenerEstadoVerificacion(token)
      .then((datos) => {
        if (vigente) setEstado(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [token])

  async function elegir(clave, archivo) {
    setError(null)
    if (!archivo) return
    if (!TIPOS_PERMITIDOS.includes(archivo.type)) {
      setError('Sube una foto en formato JPG o PNG.')
      return
    }
    if (archivo.size > TAMANO_MAXIMO) {
      setError('La foto pesa más de 5 MB. Prueba con una de menor resolución.')
      return
    }
    const dataUrl = await leerComoDataUrl(archivo)
    setFotos((anteriores) => ({ ...anteriores, [clave]: dataUrl }))
  }

  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setRechazada(false)
    setEnviando(true)
    try {
      // La API espera solo el base64: se quita el "data:image/...;base64," del comienzo
      const soloBase64 = Object.fromEntries(Object.entries(fotos).map(([clave, url]) => [clave, url.split(',')[1]]))
      const resultado = await verificarIdentidad(token, soloBase64)
      if (resultado.resultado === 'aprobado') {
        setEstado({ verificado: true, fecha: resultado.fecha })
      } else {
        setRechazada(true)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setEnviando(false)
    }
  }

  if (estado === null && !error) {
    return (
      <p role="status" className="text-sm text-tinta/65">
        Revisando tu verificación…
      </p>
    )
  }

  if (estado?.verificado) {
    return (
      <Tarjeta como="section" className="mx-auto mt-6 max-w-md p-7">
        <h1 className="text-[28px]">Tu identidad está verificada</h1>
        <p className="mt-2 text-sm text-tinta/65">
          Desde el {fechaLegible(estado.fecha)}. Ya puedes pedir y ofrecer consultas.
        </p>
        <BotonEnlace to="/mi-cuenta" className="mt-6">
          Ir a mi cuenta
        </BotonEnlace>
      </Tarjeta>
    )
  }

  const completo = FOTOS.every((foto) => fotos[foto.clave]) && consentimiento

  return (
    <section>
      <TituloPagina
        titulo="Verifica tu identidad"
        bajada="Es obligatorio para pedir y ofrecer consultas. Toma tres fotos: tu cédula por ambos lados y una selfie."
      />

      <form onSubmit={enviar} className="grid gap-5" noValidate>
        <div className="grid gap-4 md:grid-cols-3">
          {FOTOS.map((foto) => (
            <Tarjeta key={foto.clave} className="flex flex-col gap-3">
              <div>
                <h2 className="text-[15px]">{foto.titulo}</h2>
                <p className="text-xs text-tinta/65">{foto.ayuda}</p>
              </div>
              <div className="grid aspect-[4/3] place-items-center overflow-hidden rounded-2xl bg-niebla">
                {fotos[foto.clave] ? (
                  <img
                    src={fotos[foto.clave]}
                    alt={`Vista previa: ${foto.titulo}`}
                    className="size-full object-cover"
                  />
                ) : (
                  <span className="text-xs text-tinta/50">Sin foto todavía</span>
                )}
              </div>
              <label className={claseBoton('secundario', 'chico', 'cursor-pointer self-start')}>
                {fotos[foto.clave] ? 'Cambiar foto' : 'Elegir foto'}
                <input
                  type="file"
                  accept={TIPOS_PERMITIDOS.join(',')}
                  capture={foto.camara}
                  aria-label={foto.titulo}
                  className="sr-only"
                  onChange={(e) => elegir(foto.clave, e.target.files[0])}
                />
              </label>
            </Tarjeta>
          ))}
        </div>

        <div className="rounded-2xl bg-celeste p-4 text-abismo">
          <label className="flex items-start gap-3 text-sm font-semibold">
            <input
              type="checkbox"
              checked={consentimiento}
              onChange={(e) => setConsentimiento(e.target.checked)}
              aria-describedby="detalle-biometrico"
              className="mt-0.5 size-4 accent-oceano"
            />
            Autorizo el uso de mis datos biométricos para verificar mi identidad
          </label>
          <p id="detalle-biometrico" className="mt-2 pl-7 text-xs leading-relaxed opacity-90">
            Comparamos tu selfie con la foto de tu cédula y leemos tu RUN. Las imágenes se procesan y se borran apenas
            termina la verificación: no quedan guardadas en ningún servidor, respaldo ni registro. Solo guardamos el
            resultado, la fecha y una huella cifrada de tu RUN para impedir cuentas duplicadas.
          </p>
        </div>

        {rechazada && (
          <Aviso tipo="error">
            No pudimos confirmar que la selfie y la cédula sean de la misma persona. Prueba con fotos con mejor luz.
          </Aviso>
        )}
        {error && <Aviso tipo="error">{error}</Aviso>}

        <Boton type="submit" tamano="grande" disabled={!completo || enviando} className="justify-self-start">
          {enviando ? 'Verificando…' : 'Verificar mi identidad'}
        </Boton>
      </form>
    </section>
  )
}
