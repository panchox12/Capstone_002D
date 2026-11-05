import { Outlet } from 'react-router'
import { useSesion } from '../sesion/useSesion'
import { Aviso } from './ui/Aviso'
 
/** Deja pasar solo a los roles indicados; el servidor igual vuelve a revisar cada peticion. */
export function SoloPersonal({ roles }) {
  const { usuario } = useSesion()
  if (!usuario) return null
  if (!roles.includes(usuario.rol)) {
    return <Aviso tipo="error">Esta sección es solo para el equipo de Cachai.</Aviso>
  }
  return <Outlet />
}