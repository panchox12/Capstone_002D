import { Link } from 'react-router'

export function NoEncontrada() {
  return (
    <section>
      <h1 className="text-3xl font-extrabold">Esta página no existe</h1>
      <p className="mt-4">
        Revisa la dirección o{' '}
        <Link to="/" className="text-tinta underline underline-offset-4">
          vuelve al inicio
        </Link>
        .
      </p>
    </section>
  )
}
