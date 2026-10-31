import { pedir } from './cliente'
 
// Devuelve { modo, resultados }; modo dice si respondio el semantico o el lexico.
export function buscarEspecialistas(token, { duda, soloEnLinea = false, modo = 'semantico' }) {
  const parametros = new URLSearchParams({ q: duda, modo, solo_en_linea: String(soloEnLinea) })
  return pedir(`/buscar?${parametros}`, { token })
}