/*
 * Clases de Tailwind que se repiten en muchas pantallas. Estan en un solo
 * lugar para que todos los botones, tarjetas y campos de Cachai se vean
 * iguales: si cambia el diseño, se cambia aca y en ningun otro archivo.
 */

const BOTON_BASE =
  'inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-colors ' +
  'disabled:cursor-not-allowed disabled:opacity-50'

const BOTON_VARIANTES = {
  primario: 'bg-oceano text-white hover:bg-oceano-oscuro',
  secundario: 'border border-tinta/25 bg-transparent text-tinta hover:bg-tinta/5',
  claro: 'bg-white text-tinta hover:bg-niebla',
  invertido: 'border border-white bg-transparent text-white hover:bg-white/10',
}

const BOTON_TAMANOS = {
  chico: 'px-4 py-2 text-[12.5px]',
  normal: 'px-5 py-2.5 text-[13.5px]',
  grande: 'px-6 py-3 text-sm',
}

export function claseBoton(variante = 'primario', tamano = 'normal', extra = '') {
  return [BOTON_BASE, BOTON_VARIANTES[variante], BOTON_TAMANOS[tamano], extra].filter(Boolean).join(' ')
}

const TARJETA_VARIANTES = {
  blanca: 'bg-white shadow-tarjeta',
  celeste: 'bg-celeste text-abismo',
  gris: 'bg-niebla',
  oceano: 'bg-oceano text-white',
}

export function claseTarjeta(variante = 'blanca', extra = '') {
  return ['rounded-tarjeta p-5', TARJETA_VARIANTES[variante], extra].filter(Boolean).join(' ')
}

export const claseCampo =
  'w-full rounded-2xl border border-bruma bg-white px-4 py-3 text-[14.5px] text-tinta ' +
  'placeholder:text-tinta/40 hover:border-ceniza focus:border-oceano focus:outline-none'

export const claseEtiqueta = 'grid gap-1.5 text-[13px] font-semibold'

// Texto secundario: el gris azulado de las bajadas y descripciones del diseño
export const claseTextoSuave = 'text-tinta/65'
