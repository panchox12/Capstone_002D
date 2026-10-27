import { useCallback, useEffect, useMemo, useState } from 'react'
import { obtenerSaldo } from '../api/tokens'
import { useSesion } from '../sesion/useSesion'
import { ContextoSaldo } from './contexto'

// Comparte el saldo entre el encabezado, el inicio y la tienda.
export function SaldoProvider({ children }) {
  const { token, usuario } = useSesion()
  const [saldo, setSaldo] = useState(null)
  const puedeConsultar = Boolean(token) && usuario?.estado_cuenta === 'activa'

  // Se llama despues de una compra o un video
  const actualizar = useCallback(async () => {
    if (!puedeConsultar) return
    try {
      setSaldo(await obtenerSaldo(token))
    } catch {
      setSaldo(null)
    }
  }, [puedeConsultar, token])

  // Carga el saldo al entrar y cada vez que cambia la sesion
  useEffect(() => {
    if (!puedeConsultar) return undefined
    let vigente = true
    obtenerSaldo(token)
      .then((datos) => {
        if (vigente) setSaldo(datos)
      })
      .catch(() => {
        if (vigente) setSaldo(null)
      })
    return () => {
      vigente = false
    }
  }, [puedeConsultar, token])

  const valor = useMemo(
    () => ({ saldo: puedeConsultar ? saldo : null, actualizar }),
    [puedeConsultar, saldo, actualizar],
  )

  return <ContextoSaldo.Provider value={valor}>{children}</ContextoSaldo.Provider>
}