/*
 * Sonidos cortos de Cachai, generados con el navegador (Web Audio): no hay
 * archivos de audio que descargar. Se pueden apagar en Mi cuenta y la
 * preferencia queda guardada en este navegador.
 */

const CLAVE = 'cachai_sonidos'

// Cada nota: [frecuencia en Hz, inicio en segundos, duración en segundos]
const SONIDOS = {
  aviso: { forma: 'sine', volumen: 0.08, notas: [[659, 0, 0.18], [880, 0.12, 0.3]] },
  entra: { forma: 'sine', volumen: 0.07, notas: [[523, 0, 0.16], [784, 0.12, 0.26]] },
  sale: { forma: 'sine', volumen: 0.07, notas: [[784, 0, 0.16], [523, 0.12, 0.28]] },
  tiempo: { forma: 'triangle', volumen: 0.06, notas: [[880, 0, 0.12], [880, 0.2, 0.12], [880, 0.4, 0.2]] },
  clic: { forma: 'sine', volumen: 0.03, notas: [[1200, 0, 0.04]] },
}

let contexto = null

export function sonidosActivos() {
  try {
    return localStorage.getItem(CLAVE) !== 'apagados'
  } catch {
    return true
  }
}

export function cambiarSonidos(activos) {
  try {
    if (activos) localStorage.removeItem(CLAVE)
    else localStorage.setItem(CLAVE, 'apagados')
  } catch {
    // Sin almacenamiento la preferencia dura solo esta visita
  }
}

function obtenerContexto() {
  if (contexto) return contexto
  const Constructor = globalThis.AudioContext ?? globalThis.webkitAudioContext
  if (!Constructor) return null
  try {
    contexto = new Constructor()
  } catch {
    return null
  }
  return contexto
}

/** Toca un sonido por su nombre. Si el navegador no puede, no pasa nada. */
export function tocar(nombre) {
  const sonido = SONIDOS[nombre]
  if (!sonido || !sonidosActivos()) return
  const ctx = obtenerContexto()
  if (!ctx) return
  try {
    // Los navegadores silencian el audio hasta que la persona toca la página
    if (ctx.state === 'suspended') ctx.resume().catch(() => {})
    const ahora = ctx.currentTime
    for (const [frecuencia, inicio, duracion] of sonido.notas) {
      const oscilador = ctx.createOscillator()
      const volumen = ctx.createGain()
      oscilador.type = sonido.forma
      oscilador.frequency.value = frecuencia
      volumen.gain.setValueAtTime(0.0001, ahora + inicio)
      volumen.gain.exponentialRampToValueAtTime(sonido.volumen, ahora + inicio + 0.02)
      volumen.gain.exponentialRampToValueAtTime(0.0001, ahora + inicio + duracion)
      oscilador.connect(volumen).connect(ctx.destination)
      oscilador.start(ahora + inicio)
      oscilador.stop(ahora + inicio + duracion + 0.02)
    }
  } catch {
    // Un sonido nunca debe romper la pantalla
  }
}