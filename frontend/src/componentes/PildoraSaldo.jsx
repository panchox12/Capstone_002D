import { Link } from 'react-router'
import { useSaldo } from '../saldo/useSaldo'

// Saldo del encabezado; lleva al historial. En el teléfono los retenidos no caben y se ven ahí.
export function PildoraSaldo() {
  const { saldo } = useSaldo()
  if (!saldo) return null
  const retenidos = saldo.retenidos > 0 ? ` · ${saldo.retenidos} retenidos` : ''

  return (
    <Link
      to="/tokens"
      aria-label={`${saldo.total} tokens${retenidos}`}
      className="rounded-full bg-celeste px-3.5 py-1.5 text-[12.5px] font-semibold whitespace-nowrap text-abismo hover:bg-celeste-medio"
    >
      {saldo.total} tokens
      {retenidos && <span className="hidden sm:inline">{retenidos}</span>}
    </Link>
  )
}