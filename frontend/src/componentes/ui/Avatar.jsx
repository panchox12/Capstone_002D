const TAMANOS = {
  chico: 'size-8 text-[11.5px]',
  normal: 'size-10 text-[13px]',
  grande: 'size-16 text-xl',
}

const COLORES = {
  celeste: 'bg-celeste-medio text-abismo',
  gris: 'bg-bruma text-grafito',
}

function iniciales(nombre) {
  return nombre
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((palabra) => palabra[0].toUpperCase())
    .join('')
}

/** Circulo con las iniciales del nombre, como en el diseño. No usa fotos. */
export function Avatar({ nombre, tamano = 'normal', color = 'celeste', className = '' }) {
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-full font-titulo font-extrabold ${TAMANOS[tamano]} ${COLORES[color]} ${className}`}
    >
      {iniciales(nombre)}
    </span>
  )
}
