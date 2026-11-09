import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { obtenerPerfil } from '../api/perfiles'
import { enviarSolicitud } from '../api/solicitudes'
import { FormularioSolicitud } from '../componentes/FormularioSolicitud'
import { Avatar } from '../componentes/ui/Avatar'
import { Aviso } from '../componentes/ui/Aviso'
import { Boton, BotonEnlace } from '../componentes/ui/Boton'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { useSaldo } from '../saldo/useSaldo'
import { useSesion } from '../sesion/useSesion'
import { plural } from '../utilidades/formato'
 
// Igual al valor inicial de sesiones_minimas_para_estrellas.
const MINIMO_VALORACIONES = 5
 
function Reputacion({ perfil }) {
  if (perfil.total_evaluaciones < MINIMO_VALORACIONES) {
    return <p className="text-[13px] text-tinta/65">Usuario nuevo</p>
  }
  const promedio = Number(perfil.reputacion_promedio).toFixed(1).replace('.', ',')
  return (
    <p className="text-[13px] text-tinta/65">
      ★ {promedio} · {plural(perfil.total_evaluaciones, 'sesión valorada', 'sesiones valoradas')}
    </p>
  )
}
 
function FilaHabilidad({ habilidad, perfil, puedePedir, visitante, alPedir }) {
  const [abierta, setAbierta] = useState(false)
 
  return (
    <li className="border-t border-tinta/10 py-4 first:border-t-0">
      <div className="flex flex-wrap items-center gap-3">
        <p className="mr-auto text-sm font-semibold">{habilidad.tema_nombre}</p>
        <p className="text-sm">
          <span className="font-extrabold">{plural(habilidad.precio_por_bloque, 'token', 'tokens')}</span> / bloque
        </p>
        {puedePedir && !abierta && (
          <Boton
            tamano="chico"
            onClick={() => setAbierta(true)}
            aria-label={`Pedir ayuda con ${habilidad.tema_nombre}`}
          >
            Pedir ayuda
          </Boton>
        )}
        {visitante && (
          <BotonEnlace to="/ingresar" tamano="chico" variante="secundario">
            Ingresa para pedir ayuda
          </BotonEnlace>
        )}
      </div>
      {abierta && (
        <FormularioSolicitud
          tutorNombre={perfil.nombre_visible}
          enLinea={perfil.en_linea}
          precio={habilidad.precio_por_bloque}
          alEnviar={(mensaje) => alPedir(habilidad, mensaje)}
        />
      )}
    </li>
  )
}
 
// Publico: quien llega desde el buscador o desde un enlace ve al tutor antes de pedirle ayuda.
export function PerfilPublico() {
  const { identificador } = useParams()
  const { usuario, token } = useSesion()
  const { actualizar } = useSaldo()
  const navegar = useNavigate()
  const [perfil, setPerfil] = useState(null)
  const [error, setError] = useState(null)
 
  useEffect(() => {
    let vigente = true
    obtenerPerfil(identificador)
      .then((datos) => {
        if (!vigente) return
        setError(null)
        setPerfil(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [identificador])
 
  async function pedirAyuda(habilidad, mensaje) {
    const solicitud = await enviarSolicitud(token, habilidad.id, mensaje)
    actualizar()
    const aviso =
      solicitud.modalidad === 'en_vivo'
        ? `Le enviaste tu duda a ${perfil.nombre_visible}. Tiene 5 minutos para responder.`
        : `Le enviaste tu duda a ${perfil.nombre_visible}. Te avisamos cuando responda.`
    navegar('/solicitudes', { state: { aviso } })
  }
 
  if (error) return <Aviso tipo="error">{error}</Aviso>
  if (!perfil) {
    return (
      <p role="status" className="text-sm text-tinta/65">
        Cargando perfil…
      </p>
    )
  }
 
  const propio = usuario?.id === perfil.usuario_id
 
  return (
    <section className="max-w-3xl">
      <Tarjeta className="flex flex-wrap items-start gap-4 p-6">
        <Avatar nombre={perfil.nombre_visible} tamano="grande" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl">{perfil.nombre_visible}</h1>
            <Ficha variante={perfil.en_linea ? 'celeste' : 'gris'}>{perfil.en_linea ? 'En línea' : 'Desconectado'}</Ficha>
          </div>
          <Reputacion perfil={perfil} />
          {perfil.biografia && <p className="mt-3 text-sm whitespace-pre-line">{perfil.biografia}</p>}
        </div>
        {propio && (
          <BotonEnlace to="/mi-cuenta" tamano="chico" variante="secundario">
            Editar mi perfil
          </BotonEnlace>
        )}
      </Tarjeta>
 
      <Tarjeta className="mt-4 p-6">
        <h2 className="text-[17px]">En qué te puede ayudar</h2>
        {perfil.habilidades.length === 0 && (
          <p className="mt-3 text-sm text-tinta/65">Todavía no ofrece habilidades.</p>
        )}
        {perfil.habilidades.length > 0 && (
          <ul className="mt-2">
            {perfil.habilidades.map((habilidad) => (
              <FilaHabilidad
                key={habilidad.id}
                habilidad={habilidad}
                perfil={perfil}
                puedePedir={Boolean(usuario) && !propio}
                visitante={!usuario}
                alPedir={pedirAyuda}
              />
            ))}
          </ul>
        )}
      </Tarjeta>
    </section>
  )
}