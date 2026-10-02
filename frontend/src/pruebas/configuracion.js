import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Cada prueba parte de cero: sin pantalla, sin token guardado y sin fetch falso
afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.unstubAllGlobals()
})
