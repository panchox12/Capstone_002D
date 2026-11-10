import { Link, NavLink, Outlet } from 'react-router'
import { SaldoProvider } from '../saldo/SaldoProvider'
import { useSesion } from '../sesion/useSesion'
import { Campana } from './Campana'
import { MenuCuenta } from './MenuCuenta'
import { PildoraSaldo } from './PildoraSaldo'
import { BotonEnlace } from './ui/Boton'
import { Logo } from './ui/Logo'

function claseEnlace({ isActive }) {
  return isActive
    ? 'text-[13.5px] font-semibold text-oceano-oscuro'
    : 'text-[13.5px] text-tinta hover:text-oceano-oscuro'
}

/** Lo que se repite en todas las paginas: el encabezado y el contenedor del contenido. */
export function Plantilla() {
  const { usuario } = useSesion()

  // El encabezado y las paginas comparten el mismo saldo
  return (
    <SaldoProvider>
      <div className="min-h-screen">
        <header className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-5 gap-y-3 px-5 py-4 sm:px-7">
          <Link to="/" className="mr-auto" aria-label="Cachai, ir al inicio">
            <Logo />
          </Link>

          {/* En el teléfono el menú baja a su propia fila y se desliza de lado */}
          <nav
            aria-label="Principal"
            className={
              usuario
                ? 'order-last -mx-1 flex w-full gap-x-5 overflow-x-auto px-1 pb-1 whitespace-nowrap [scrollbar-width:none] lg:order-none lg:mx-0 lg:w-auto lg:overflow-visible lg:p-0'
                : 'flex items-center gap-x-5'
            }
          >
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
                <NavLink to="/sesiones" className={claseEnlace}>
                  Sesiones
                </NavLink>
                <NavLink to="/temas" className={claseEnlace}>
                  Temas
                </NavLink>
                <NavLink to="/tienda" className={claseEnlace}>
                  Tienda
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
            <div className="flex items-center gap-2 sm:gap-3">
              <Campana />
              <PildoraSaldo />
              <MenuCuenta />
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