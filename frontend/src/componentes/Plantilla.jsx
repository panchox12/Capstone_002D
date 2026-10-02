import { Link, NavLink, Outlet } from 'react-router'
import { useSesion } from '../sesion/useSesion'

function claseEnlace({ isActive }) {
  return isActive ? 'font-bold text-tinta underline underline-offset-4' : 'text-grafito hover:text-tinta'
}

/** Lo que se repite en todas las paginas: el encabezado y el contenedor del contenido. */
export function Plantilla() {
  const { usuario, salir } = useSesion()

  return (
    <div className="min-h-screen">
      <header className="border-b border-niebla">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-4 px-5 py-4">
          <Link to="/" className="resaltado font-titulo text-2xl font-extrabold text-tinta">
            cachai
          </Link>

          <nav aria-label="Principal" className="flex flex-wrap items-center gap-5">
            <NavLink to="/temas" className={claseEnlace}>
              Temas
            </NavLink>
            {usuario ? (
              <>
                <NavLink to="/mi-cuenta" className={claseEnlace}>
                  {usuario.nombre_visible}
                </NavLink>
                <button
                  type="button"
                  onClick={salir}
                  className="rounded-md border border-tinta px-3 py-1.5 text-tinta hover:bg-niebla"
                >
                  Cerrar sesión
                </button>
              </>
            ) : (
              <NavLink to="/ingresar" className={claseEnlace}>
                Ingresar
              </NavLink>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-5 py-10">
        <Outlet />
      </main>
    </div>
  )
}
