import { pedir } from './cliente'

// Los paquetes se pueden ver sin sesion.
export function obtenerPaquetes() {
  return pedir('/tienda/paquetes')
}

export function comprarPaquete(token, codigo) {
  return pedir('/tienda/compras', { metodo: 'POST', token, json: { paquete: codigo } })
}

export function obtenerCompras(token) {
  return pedir('/tienda/compras', { token })
}