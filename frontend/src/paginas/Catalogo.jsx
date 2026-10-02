import { useEffect, useState } from 'react'
import { obtenerCatalogo } from '../api/temas'

/** Catalogo de tres niveles, leido de GET /temas. Es publico. */
export function Catalogo() {
  const [temas, setTemas] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let vigente = true
    obtenerCatalogo()
      .then((datos) => {
        if (vigente) setTemas(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [])

  if (error) {
    return (
      <p role="alert" className="text-alerta">
        No pudimos cargar los temas. {error}
      </p>
    )
  }
  if (temas === null) {
    return <p role="status">Cargando temas…</p>
  }
  if (temas.length === 0) {
    return <p>Todavía no hay temas publicados.</p>
  }

  return (
    <section>
      <h1 className="text-3xl font-extrabold">Temas</h1>
      <p className="mt-2">Estos son los temas en los que puedes pedir ayuda.</p>
      <div className="mt-8 grid gap-10">
        {temas.map((area) => (
          <article key={area.id}>
            <h2 className="text-2xl font-bold">{area.nombre}</h2>
            {area.hijos.map((materia) => (
              <div key={materia.id} className="mt-4">
                <h3 className="text-lg font-semibold">{materia.nombre}</h3>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {materia.hijos.map((tema) => (
                    <li key={tema.id} className="rounded-full bg-niebla px-3 py-1">
                      {tema.nombre}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </article>
        ))}
      </div>
    </section>
  )
}
