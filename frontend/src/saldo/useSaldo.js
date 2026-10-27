import { useContext } from 'react'
import { ContextoSaldo } from './contexto'

export function useSaldo() {
  const saldo = useContext(ContextoSaldo)
  if (saldo === null) {
    throw new Error('useSaldo debe usarse dentro de <SaldoProvider>')
  }
  return saldo
}