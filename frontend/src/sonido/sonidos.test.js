import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// AudioContext falso: registra cuantas notas se tocan
function audioFalso() {
  const notas = []
  class ContextoFalso {
    state = 'running'
    currentTime = 0
    destination = {}
    createOscillator() {
      const nota = { type: '', frequency: { value: 0 }, connect: (x) => x, start: vi.fn(), stop: vi.fn() }
      notas.push(nota)
      return nota
    }
    createGain() {
      return {
        gain: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() },
        connect: (x) => x,
      }
    }
    resume() {
      return Promise.resolve()
    }
  }
  vi.stubGlobal('AudioContext', ContextoFalso)
  return notas
}

// El modulo guarda el contexto de audio: cada prueba lo carga de nuevo
async function cargar() {
  vi.resetModules()
  return import('./sonidos')
}

describe('sonidos', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.unstubAllGlobals())

  it('vienen encendidos por defecto', async () => {
    const { sonidosActivos } = await cargar()

    expect(sonidosActivos()).toBe(true)
  })

  it('apagarlos queda guardado en el navegador', async () => {
    const { cambiarSonidos, sonidosActivos } = await cargar()

    cambiarSonidos(false)

    expect(sonidosActivos()).toBe(false)
    expect(localStorage.getItem('cachai_sonidos')).toBe('apagados')
    cambiarSonidos(true)
    expect(sonidosActivos()).toBe(true)
  })

  it('el aviso toca dos notas', async () => {
    const notas = audioFalso()
    const { tocar } = await cargar()

    tocar('aviso')

    expect(notas.map((n) => n.frequency.value)).toEqual([659, 880])
    expect(notas.every((n) => n.start.mock.calls.length === 1)).toBe(true)
  })

  it('con los sonidos apagados no suena nada', async () => {
    const notas = audioFalso()
    const { cambiarSonidos, tocar } = await cargar()

    cambiarSonidos(false)
    tocar('aviso')

    expect(notas).toHaveLength(0)
  })

  it('sin audio en el navegador no falla', async () => {
    vi.stubGlobal('AudioContext', undefined)
    const { tocar } = await cargar()

    expect(() => tocar('tiempo')).not.toThrow()
  })
})