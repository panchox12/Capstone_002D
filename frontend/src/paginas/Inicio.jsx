import { useSesion } from '../sesion/useSesion'
import { BotonEnlace } from '../componentes/ui/Boton'
import { Tarjeta } from '../componentes/ui/Tarjeta'
import { Panel } from './Panel'

const PASOS = [
  {
    titulo: 'Cuenta tu duda como se la contarías a un amigo',
    texto: 'No necesitas saber cómo se llama el tema. Lo escribes con tus palabras.',
  },
  {
    titulo: 'Elige a alguien y envíale tu duda',
    texto: 'Ves su precio antes de pedir. Si no te responde a tiempo, tus tokens vuelven solos.',
  },
  {
    titulo: 'Pagas solo el bloque que usas',
    texto: 'Cada bloque dura quince minutos. Sin suscripción y sin cobros automáticos.',
  },
]

export function Inicio() {
  const { usuario } = useSesion()

  // Con sesion iniciada, el inicio es el panel con el saldo
  if (usuario) {
    return <Panel />
  }

  return (
    <section className="grid items-center gap-10 py-6 lg:grid-cols-[1.15fr_1fr]">
      <div>
        <h1 className="text-4xl leading-[1.08] sm:text-5xl">Tu duda, resuelta en quince minutos.</h1>
        <p className="mt-5 max-w-xl text-lg leading-relaxed text-tinta/65">
          Conéctate por videollamada con alguien que sabe del tema. Matemáticas, electricidad, inglés o la película que
          no entendiste: pagas con tokens solo el bloque que usas.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <BotonEnlace to="/temas" tamano="grande">
            Ver los temas
          </BotonEnlace>
          <BotonEnlace to="/crear-cuenta" variante="secundario" tamano="grande">
            Crear cuenta
          </BotonEnlace>
        </div>
      </div>

      <div className="grid gap-3.5">
        <Tarjeta variante="celeste" className="px-6 py-5">
          <p className="flex items-baseline gap-2">
            <span className="font-titulo text-[40px] leading-none font-extrabold">10</span>
            <span className="text-[13.5px] font-semibold">tokens gratuitos cada lunes</span>
          </p>
          <p className="mt-2 text-xs opacity-85">Y uno más por cada video que veas, hasta tres al día.</p>
        </Tarjeta>
        {PASOS.map((paso, numero) => (
          <Tarjeta key={paso.titulo} className="grid grid-cols-[32px_1fr] gap-x-3">
            <span className="grid size-8 place-items-center rounded-full bg-celeste text-[13px] font-extrabold text-abismo">
              {numero + 1}
            </span>
            <div>
              <h2 className="text-[15px] leading-snug">{paso.titulo}</h2>
              <p className="mt-1 text-[13px] text-tinta/65">{paso.texto}</p>
            </div>
          </Tarjeta>
        ))}
      </div>
    </section>
  )
}