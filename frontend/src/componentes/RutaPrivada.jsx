import { Navigate, Outlet, useLocation } from 'react-router'
import { useSesion } from '../sesion/useSesion'

/**
 * Envuelve las rutas que exigen sesion. Sin sesion, manda a /ingresar y
 * recuerda de donde venia, para volver ahi despues de iniciar sesion.
 */
export function RutaPrivada() {
  const { usuario, cargando } = useSesion()
  const ubicacion = useLocation()

  if (cargando) {
    return <p role="status">Cargando tu sesión…</p>
  }
  if (!usuario) {
    return <Navigate to="/ingresar" replace state={{ desde: ubicacion.pathname }} />
  }
  return <Outlet />
}
