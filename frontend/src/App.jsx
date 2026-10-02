import { Route, Routes } from 'react-router'
import { Plantilla } from './componentes/Plantilla'
import { RutaPrivada } from './componentes/RutaPrivada'
import { Catalogo } from './paginas/Catalogo'
import { Ingresar } from './paginas/Ingresar'
import { Inicio } from './paginas/Inicio'
import { MiCuenta } from './paginas/MiCuenta'
import { NoEncontrada } from './paginas/NoEncontrada'

export default function App() {
  return (
    <Routes>
      <Route element={<Plantilla />}>
        <Route index element={<Inicio />} />
        <Route path="temas" element={<Catalogo />} />
        <Route path="ingresar" element={<Ingresar />} />
        <Route element={<RutaPrivada />}>
          <Route path="mi-cuenta" element={<MiCuenta />} />
        </Route>
        <Route path="*" element={<NoEncontrada />} />
      </Route>
    </Routes>
  )
}
