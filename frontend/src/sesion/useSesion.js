import { useContext } from 'react'
import { ContextoSesion } from './contexto'

export function useSesion() {
  const sesion = useContext(ContextoSesion)
  if (sesion === null) {
    throw new Error('useSesion debe usarse dentro de <SesionProvider>')
  }
  return sesion
}
