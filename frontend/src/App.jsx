import { Route, Routes } from 'react-router'
import { Plantilla } from './componentes/Plantilla'
import { RutaPrivada } from './componentes/RutaPrivada'
import { Catalogo } from './paginas/Catalogo'
import { ConfirmarCorreo } from './paginas/ConfirmarCorreo'
import { CrearCuenta } from './paginas/CrearCuenta'
import { Ingresar } from './paginas/Ingresar'
import { Inicio } from './paginas/Inicio'
import { MiCuenta } from './paginas/MiCuenta'
import { NoEncontrada } from './paginas/NoEncontrada'
import { Verificar } from './paginas/Verificar'


export default function App() {
  return (
    <Routes>
      <Route element={<Plantilla />}>
        <Route index element={<Inicio />} />
        <Route path="temas" element={<Catalogo />} />
        <Route path="ingresar" element={<Ingresar />} />
        <Route path="crear-cuenta" element={<CrearCuenta />} />
        <Route path="confirmar/:token" element={<ConfirmarCorreo />} />
        <Route element={<RutaPrivada />}>
          <Route path="mi-cuenta" element={<MiCuenta />} />
          <Route path="verificar" element={<Verificar />} />
        </Route>
        <Route path="*" element={<NoEncontrada />} />
      </Route>
    </Routes>
  )
}
