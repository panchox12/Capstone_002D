import { Link } from 'react-router'
import { useSesion } from '../sesion/useSesion'

export function Inicio() {
  const { usuario } = useSesion()

  return (
    <section className="max-w-2xl py-6">
      <h1 className="text-4xl leading-tight font-extrabold sm:text-5xl">
        Tu duda, resuelta en quince minutos.
      </h1>
      <p className="mt-5 text-lg leading-relaxed">
        Conéctate por videollamada con alguien que sabe del tema. Matemáticas, electricidad, inglés o la
        película que no entendiste: pagas con tokens solo el bloque que usas.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link to="/temas" className="rounded-md bg-resaltador px-5 py-3 font-bold text-tinta hover:brightness-95">
          Ver los temas
        </Link>
        {!usuario && (
          <Link to="/ingresar" className="rounded-md border border-tinta px-5 py-3 text-tinta hover:bg-niebla">
            Ingresar
          </Link>
        )}
      </div>
    </section>
  )
}
