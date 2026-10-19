const TIPOS = {
  error: { rol: 'alert', clases: 'bg-alerta/10 text-alerta' },
  info: { rol: 'status', clases: 'bg-celeste text-abismo' },
  exito: { rol: 'status', clases: 'bg-acierto/10 text-acierto' },
  neutro: { rol: 'status', clases: 'bg-niebla text-tinta/80' },
}

/** Mensaje en una franja de color. Los errores usan role="alert" para que los lectores de pantalla los anuncien. */
export function Aviso({ tipo = 'info', className = '', children }) {
  const { rol, clases } = TIPOS[tipo]
  return (
    <p role={rol} className={`rounded-2xl px-4 py-3 text-[13.5px] ${clases} ${className}`}>
      {children}
    </p>
  )
}
