// 905 segundos -> "15:05". Los relojes de la sala usan siempre minutos y segundos.
export function reloj(segundos) {
  const total = Math.max(0, Math.floor(segundos))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

export const ESTADOS_SESION = {
  esperando: { texto: 'Esperando conexión', variante: 'celeste' },
  en_curso: { texto: 'En curso', variante: 'celeste' },
  terminada: { texto: 'Terminada', variante: 'gris' },
  cancelada: { texto: 'Cancelada', variante: 'gris' },
}