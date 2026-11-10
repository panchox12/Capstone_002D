import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useSesion } from '../sesion/useSesion'
import { Avatar } from './ui/Avatar'

const CLASE_OPCION = 'block w-full rounded-xl px-3 py-2 text-left text-[13.5px] hover:bg-niebla'

// Menú del avatar: la cuenta, las secciones del equipo y cerrar sesión.
export function MenuCuenta() {
  const { usuario, salir } = useSesion()
  const [abierto, setAbierto] = useState(false)
  const caja = useRef(null)

  // Se cierra al tocar fuera o con Escape
  useEffect(() => {
    if (!abierto) return undefined
    const fuera = (evento) => {
      if (caja.current && !caja.current.contains(evento.target)) setAbierto(false)
    }
    const escape = (evento) => {
      if (evento.key === 'Escape') setAbierto(false)
    }
    document.addEventListener('pointerdown', fuera)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('pointerdown', fuera)
      document.removeEventListener('keydown', escape)
    }
  }, [abierto])

  const cerrar = () => setAbierto(false)
  const esPersonal = usuario.rol === 'soporte' || usuario.rol === 'administrador'

  return (
    <div className="relative" ref={caja}>
      <button
        type="button"
        aria-label="Menú de tu cuenta"
        aria-expanded={abierto}
        onClick={() => setAbierto((a) => !a)}
        className="rounded-full"
      >
        <Avatar nombre={usuario.nombre_visible} tamano="chico" />
      </button>
      {abierto && (
        <div className="absolute right-0 z-20 mt-2 w-60 rounded-tarjeta bg-white p-2 shadow-flotante">
          <div className="border-b border-tinta/10 px-3 pt-1 pb-2">
            <p className="truncate text-sm font-semibold">{usuario.nombre_visible}</p>
            <p className="truncate text-xs text-tinta/65">{usuario.correo}</p>
          </div>
          <nav aria-label="Tu cuenta" className="mt-1 grid">
            <Link to="/mi-cuenta" className={CLASE_OPCION} onClick={cerrar}>
              Mi cuenta
            </Link>
            {esPersonal && (
              <Link to="/soporte" className={CLASE_OPCION} onClick={cerrar}>
                Soporte
              </Link>
            )}
            {usuario.rol === 'administrador' && (
              <Link to="/admin" className={CLASE_OPCION} onClick={cerrar}>
                Administración
              </Link>
            )}
            <button
              type="button"
              className={`${CLASE_OPCION} border-t border-tinta/10 text-alerta`}
              onClick={() => {
                cerrar()
                salir()
              }}
            >
              Cerrar sesión
            </button>
          </nav>
        </div>
      )}
    </div>
  )
}