/** Globo de dialogo con un ojo y una sonrisa, mas el nombre en minusculas. */
export function Logo() {
  return (
    <span className="inline-flex items-center gap-2 font-titulo text-lg font-extrabold tracking-tighter text-tinta">
      <svg width="24" height="24" viewBox="0 0 48 48" aria-hidden="true">
        <path
          d="M4 0 H44 A4 4 0 0 1 48 4 V32 A4 4 0 0 1 44 36 H20 L9 47 A1.4 1.4 0 0 1 8 45.6 V36 H4 A4 4 0 0 1 0 32 V4 A4 4 0 0 1 4 0 Z"
          className="fill-oceano"
        />
        <path d="M24 18 V6 A12 12 0 0 1 36 18 Z" className="fill-fondo" />
        <circle cx="16" cy="18" r="4" className="fill-fondo" />
      </svg>
      cachai
    </span>
  )
}
