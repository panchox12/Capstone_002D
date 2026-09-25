"""Carga el catalogo inicial de temas.
 
Se puede ejecutar varias veces: los temas que ya existen no se duplican.
Los nombres llevan tildes porque son datos que ven los usuarios, no codigo.
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
 
 
def sembrar() -> None:
    db = SesionLocal()
    try:
        antes = db.scalar(select(func.count()).select_from(Tema))
        for raiz, grupos in CATALOGO.items():
            tema_raiz = obtener_o_crear(db, raiz)
            for grupo, hojas in grupos.items():
                tema_grupo = obtener_o_crear(db, grupo, tema_raiz.id)
                for hoja in hojas:
                    obtener_o_crear(db, hoja, tema_grupo.id)
        db.commit()
        despues = db.scalar(select(func.count()).select_from(Tema))
        print(f"Temas creados: {despues - antes}")
    finally:
        db.close()
 
 
if __name__ == "__main__":
    sembrar()