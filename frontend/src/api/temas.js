import { pedir } from './cliente'

/** Catalogo completo, publico: no necesita sesion. */
export function obtenerCatalogo() {
  return pedir('/temas')
}
