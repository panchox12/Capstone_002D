import { Link } from 'react-router'
import { claseBoton } from './clases'

/** Boton con forma de pildora. Variantes: primario, secundario, claro, invertido. */
export function Boton({ variante = 'primario', tamano = 'normal', className = '', type = 'button', ...resto }) {
  return <button type={type} className={claseBoton(variante, tamano, className)} {...resto} />
}

/** Un enlace que se ve como boton: para ir a otra pagina, no para ejecutar una accion. */
export function BotonEnlace({ variante = 'primario', tamano = 'normal', className = '', ...resto }) {
  return <Link className={claseBoton(variante, tamano, className)} {...resto} />
}
