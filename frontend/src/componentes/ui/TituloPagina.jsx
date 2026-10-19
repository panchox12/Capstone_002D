/** El titulo grande de cada pantalla, con su bajada en gris. */
export function TituloPagina({ titulo, bajada, children }) {
  return (
    <header className="mb-6">
      <h1 className="text-[31px] leading-tight">{titulo}</h1>
      {bajada && <p className="mt-1 text-sm text-tinta/65">{bajada}</p>}
      {children}
    </header>
  )
}
