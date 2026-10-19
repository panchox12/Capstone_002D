import { claseTarjeta } from './clases'

/**
 * Bloque redondeado del diseño. Variantes: blanca (con sombra), celeste,
 * gris y oceano. "como" permite cambiar la etiqueta HTML, por ejemplo a
 * article o section, sin perder el estilo.
 */
export function Tarjeta({ variante = 'blanca', como: Etiqueta = 'div', className = '', ...resto }) {
  return <Etiqueta className={claseTarjeta(variante, className)} {...resto} />
}
