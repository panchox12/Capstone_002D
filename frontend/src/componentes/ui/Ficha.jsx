const VARIANTES = {
  celeste: 'bg-celeste text-abismo',
  gris: 'bg-niebla text-grafito',
  contorno: 'border border-oceano bg-white text-oceano',
}

/** Etiqueta chica con forma de pildora: estados, temas, avisos cortos. */
export function Ficha({ variante = 'celeste', className = '', ...resto }) {
  const clases = `inline-flex items-center rounded-full px-3 py-1 text-[11.5px] font-semibold ${VARIANTES[variante]} ${className}`
  return <span className={clases} {...resto} />
}
