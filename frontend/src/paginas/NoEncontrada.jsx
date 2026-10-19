import { BotonEnlace } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'

export function NoEncontrada() {
  return (
    <Tarjeta como="section" className="mx-auto mt-6 max-w-md p-7 text-center">
      <h1 className="text-[28px]">Esta página no existe</h1>
      <p className="mt-2 text-sm text-tinta/65">Revisa la dirección o vuelve al inicio.</p>
      <BotonEnlace to="/" className="mt-6">
        Volver al inicio
      </BotonEnlace>
    </Tarjeta>
  )
}
