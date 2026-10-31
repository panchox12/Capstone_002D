import { Link, NavLink, Outlet } from 'react-router'
import { SaldoProvider } from '../saldo/SaldoProvider'
import { useSesion } from '../sesion/useSesion'
import { PildoraSaldo } from './PildoraSaldo'
import { Avatar } from './ui/Avatar'
import { Boton, BotonEnlace } from './ui/Boton'
import { Logo } from './ui/Logo'

function claseEnlace({ isActive }) {
  return isActive
    ? 'text-[13.5px] font-semibold text-oceano-oscuro'
    : 'text-[13.5px] text-tinta hover:text-oceano-oscuro'
}

/** Lo que se repite en todas las paginas: el encabezado y el contenedor del contenido. */
export function Plantilla() {
  const { usuario, salir } = useSesion()

  // El encabezado y las paginas comparten el mismo saldo
  return (
    <SaldoProvider>
      <div className="min-h-screen">
        <header className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-5 gap-y-3 px-5 py-4 sm:px-7">
          <Link to="/" className="mr-auto" aria-label="Cachai, ir al inicio">
            <Logo />
          </Link>

          <nav aria-label="Principal" className="flex flex-wrap items-center gap-x-5 gap-y-2">
            {usuario ? (
              <>
                <NavLink to="/" end className={claseEnlace}>
                  Inicio
                </NavLink>
                <NavLink to="/buscar" className={claseEnlace}>
                  Buscar
                </NavLink>
                <NavLink to="/solicitudes" className={claseEnlace}>
                  Solicitudes
                </NavLink>
                <NavLink to="/temas" className={claseEnlace}>
                  Temas
                </NavLink>
                <NavLink to="/tienda" className={claseEnlace}>
                  Tienda
                </NavLink>
                <NavLink to="/mi-cuenta" className={claseEnlace}>
                  Mi cuenta
                </NavLink>
              </>
            ) : (
              <>
                <NavLink to="/temas" className={claseEnlace}>
                  Temas
                </NavLink>
                <NavLink to="/ingresar" className={claseEnlace}>
                  Ingresar
                </NavLink>
              </>
            )}
          </nav>

          {!usuario && (
            <BotonEnlace to="/crear-cuenta" tamano="chico">
              Crear cuenta
            </BotonEnlace>
          )}

          {usuario && (
            <div className="flex items-center gap-3">
              <PildoraSaldo />
              <Avatar nombre={usuario.nombre_visible} tamano="chico" />
              <Boton variante="secundario" tamano="chico" onClick={salir}>
                Cerrar sesión
              </Boton>
            </div>
          )}
        </header>

        <main className="mx-auto max-w-6xl px-5 pt-4 pb-14 sm:px-7">
          <Outlet />
        </main>
      </div>
    </SaldoProvider>
  )
}