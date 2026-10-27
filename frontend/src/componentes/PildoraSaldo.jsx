import { Link } from 'react-router'
import { useSaldo } from '../saldo/useSaldo'

// Saldo del encabezado; lleva a la tienda.
export function PildoraSaldo() {
  const { saldo } = useSaldo()
  if (!saldo) return null

  return (
    <Link
      to="/tienda"
      className="rounded-full bg-celeste px-3.5 py-1.5 text-[12.5px] font-semibold text-abismo hover:bg-celeste-medio"
    >
      {saldo.total} tokens
      {saldo.retenidos > 0 && ` · ${saldo.retenidos} retenidos`}
    </Link>
  )
}