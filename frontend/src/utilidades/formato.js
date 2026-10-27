/*
 * Formato chileno para mostrar montos y fechas.
 */

const PESOS = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' })

export function pesos(monto) {
  return PESOS.format(monto)
}

export function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-CL', { day: 'numeric', month: 'short', year: 'numeric' })
}

const MILISEGUNDOS_POR_DIA = 24 * 60 * 60 * 1000

// Redondea hacia arriba: si vence en 2 horas, cuenta 1 dia.
export function diasHasta(iso, ahora = Date.now()) {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - ahora) / MILISEGUNDOS_POR_DIA))
}

export function plural(cantidad, singular, varios) {
  return `${cantidad} ${cantidad === 1 ? singular : varios}`
}