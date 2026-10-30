"""Carga el catalogo inicial de temas.

Se puede ejecutar varias veces: los temas que ya existen no se duplican.
Las descripciones le dan contexto al buscador semantico; si se cambian,
hay que volver a correr scripts.calcular_embeddings.
"""

from sqlalchemy import func, select

from app.db.sesion import SesionLocal
from app.modelos.tema import Tema
from app.servicios.temas import obtener_o_crear

CATALOGO = {
    "Ciencias exactas": {
        "Matemáticas": ["Álgebra", "Cálculo", "Geometría"],
        "Física": ["Mecánica", "Electricidad y magnetismo"],
    },
    "Oficios": {
        "Electricidad": ["Instalaciones eléctricas domiciliarias"],
        "Construcción": ["Albañilería", "Gasfitería"],
    },
    "Lenguaje": {
        "Lengua castellana": ["Redacción", "Ortografía"],
        "Idiomas": ["Inglés"],
    },
    "Tecnología": {
        "Programación": ["Python", "Desarrollo web"],
        "Computación": ["Excel", "Soporte de computadores"],
    },
    "Cultura popular": {
        "Cine y series": ["Explicación de películas"],
        "Anime": ["Dudas de anime"],
    },
}

DESCRIPCIONES = {
    "Álgebra": "Ecuaciones, incógnitas, factorización, polinomios y fracciones algebraicas.",
    "Cálculo": "Límites, derivadas, integrales y sus aplicaciones.",
    "Geometría": "Áreas, perímetros, volúmenes, ángulos y figuras planas y sólidas.",
    "Mecánica": "Movimiento, velocidad, aceleración, fuerzas y energía.",
    "Electricidad y magnetismo": "Circuitos, corriente, voltaje, imanes y campos magnéticos.",
    "Instalaciones eléctricas domiciliarias": "Interruptores, tableros, cables, circuitos de la casa y cortes de luz.",
    "Albañilería": "Muros, ladrillos, cemento, estucos y arreglos de construcción.",
    "Gasfitería": "Cañerías, filtraciones, desagües, calefont y artefactos del baño y la cocina.",
    "Redacción": "Informes, ensayos, currículum y textos claros y ordenados.",
    "Ortografía": "Acentuación, puntuación, uso de letras y reglas de escritura.",
    "Inglés": "Conversación, gramática, vocabulario y pruebas de inglés.",
    "Python": "Programas en Python, mensajes de error, listas, funciones y librerías.",
    "Desarrollo web": "Sitios con HTML, CSS y JavaScript, diseño adaptable y publicación.",
    "Excel": "Fórmulas, gráficos, filtros y planillas de cálculo.",
    "Soporte de computadores": "Virus, instalación de programas, Windows, respaldos y equipos que fallan.",
    "Explicación de películas": "Tramas, finales y detalles de películas y series.",
    "Dudas de anime": "Personajes, sagas, temporadas y recomendaciones de anime.",
}


def sembrar() -> None:
    db = SesionLocal()
    try:
        antes = db.scalar(select(func.count()).select_from(Tema))
        for raiz, grupos in CATALOGO.items():
            tema_raiz = obtener_o_crear(db, raiz)
            for grupo, hojas in grupos.items():
                tema_grupo = obtener_o_crear(db, grupo, tema_raiz.id)
                for hoja in hojas:
                    tema = obtener_o_crear(db, hoja, tema_grupo.id)
                    # Tambien completa la descripcion de los temas que ya existian.
                    tema.descripcion = DESCRIPCIONES.get(hoja, tema.descripcion)
        db.commit()
        despues = db.scalar(select(func.count()).select_from(Tema))
        print(f"Temas creados: {despues - antes}")
    finally:
        db.close()


if __name__ == "__main__":
    sembrar()