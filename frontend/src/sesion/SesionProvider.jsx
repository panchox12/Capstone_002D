import { useCallback, useEffect, useMemo, useState } from 'react'
import { iniciarSesion, obtenerUsuarioActual } from '../api/auth'
import { registrarAlExpirarSesion } from '../api/cliente'
import { avisarDesconexion, enviarLatido, MILISEGUNDOS_ENTRE_LATIDOS } from '../api/presencia'
import { ContextoSesion } from './contexto'

const CLAVE_TOKEN = 'cachai_token'

function leerTokenGuardado() {
  try {
    return localStorage.getItem(CLAVE_TOKEN)
  } catch {
    return null
  }
}

/**
 * Guarda quien inicio sesion y lo comparte con toda la aplicacion.
 * El token sobrevive a recargar la pagina porque se guarda en localStorage;
 * los datos del usuario se vuelven a pedir a la API con ese token.
 */
export function SesionProvider({ children }) {
  const [token, setToken] = useState(leerTokenGuardado)
  const [usuario, setUsuario] = useState(null)

  const salir = useCallback(() => {
    // Aviso de desconexion "de cortesia": si falla, la marca en Redis vence sola igual
    const tokenAnterior = localStorage.getItem(CLAVE_TOKEN)
    if (tokenAnterior) avisarDesconexion(tokenAnterior).catch(() => {})
    localStorage.removeItem(CLAVE_TOKEN)
    setToken(null)
    setUsuario(null)
  }, [])

  // Si cualquier peticion recibe un 401, la sesion se cierra sola
  useEffect(() => {
    registrarAlExpirarSesion(salir)
    return () => registrarAlExpirarSesion(null)
  }, [salir])

  // Cada vez que cambia el token, se piden los datos del usuario
  useEffect(() => {
    if (!token) return undefined
    let vigente = true
    obtenerUsuarioActual(token)
      .then((datos) => {
        if (vigente) setUsuario(datos)
      })
      .catch(() => {
        if (vigente) salir()
      })
    return () => {
      vigente = false
    }
  }, [token, salir])

  // Mientras haya sesion, un latido al entrar y otro cada 30 segundos
  useEffect(() => {
    if (!usuario) return undefined
    const latir = () => enviarLatido(token).catch(() => {})
    latir()
    const intervalo = setInterval(latir, MILISEGUNDOS_ENTRE_LATIDOS)
    return () => clearInterval(intervalo)
  }, [usuario, token])

  const ingresar = useCallback(async (correo, contrasena) => {
    const { access_token: nuevoToken } = await iniciarSesion(correo, contrasena)
    localStorage.setItem(CLAVE_TOKEN, nuevoToken)
    setUsuario(null)
    setToken(nuevoToken)
  }, [])

  // Hay token pero todavia no llegan los datos: la sesion se esta cargando
  const cargando = Boolean(token) && usuario === null

  const valor = useMemo(
    () => ({ token, usuario, cargando, ingresar, salir }),
    [token, usuario, cargando, ingresar, salir],
  )

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
}
