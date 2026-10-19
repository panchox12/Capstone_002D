import { useEffect, useState } from 'react'
import { obtenerCatalogo } from '../api/temas'
import { Aviso } from '../componentes/ui/Aviso'
import { Ficha } from '../componentes/ui/Ficha'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { TituloPagina } from '../componentes/ui/TituloPagina'

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
    return <Aviso tipo="error">No pudimos cargar los temas. {error}</Aviso>
  }
  if (temas === null) {
    return (
      <p role="status" className="text-sm text-tinta/65">
        Cargando temas…
      </p>
    )
  }
  if (temas.length === 0) {
    return <Aviso tipo="neutro">Todavía no hay temas publicados.</Aviso>
  }

  return (
    <section>
      <TituloPagina titulo="Temas" bajada="Estos son los temas en los que puedes pedir ayuda." />
      <div className="grid gap-4 md:grid-cols-2">
        {temas.map((area) => (
          <Tarjeta key={area.id} como="article" className="p-6">
            <h2 className="text-xl">{area.nombre}</h2>
            {area.hijos.map((materia) => (
              <div key={materia.id} className="mt-4">
                <h3 className="text-[15px]">{materia.nombre}</h3>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {materia.hijos.map((tema) => (
                    <li key={tema.id}>
                      <Ficha>{tema.nombre}</Ficha>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </Tarjeta>
        ))}
      </div>
    </section>
  )
}
