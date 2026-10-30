"""Compara el buscador lexico con el semantico sobre un conjunto de dudas de prueba.

Cada fila de consultas_prueba.csv tiene una duda y el tema que deberia
encontrar. Para cada modo se mide:
- acierto@1: el tema correcto quedo primero.
- acierto@3: el tema correcto quedo entre los tres primeros.
- MRR: promedio de 1 / posicion del tema correcto (0 si no aparece).
Se ejecuta con: python -m scripts.evaluar_buscador
"""

import csv
from pathlib import Path

from sqlalchemy import select

from app.db.sesion import SesionLocal
from app.modelos.tema import Tema
from app.servicios import buscador, embeddings

ARCHIVO = Path(__file__).with_name("consultas_prueba.csv")


def _posicion(temas: list[tuple[int, float]], tema_id: int) -> int | None:
    for indice, (candidato, _) in enumerate(temas, start=1):
        if candidato == tema_id:
            return indice
    return None


def evaluar() -> None:
    db = SesionLocal()
    try:
        ids = {tema.nombre: tema.id for tema in db.execute(select(Tema)).scalars()}
        filas = list(csv.DictReader(ARCHIVO.open(encoding="utf-8")))
        print(f"Consultas: {len(filas)} | modelo semantico: {embeddings.nombre_modelo()}\n")

        for modo, funcion in (("lexico", buscador.temas_lexicos), ("semantico", buscador.temas_semanticos)):
            al_primero = entre_tres = reciprocos = 0.0
            for fila in filas:
                posicion = _posicion(funcion(db, fila["consulta"]), ids[fila["tema_esperado"]])
                al_primero += posicion == 1
                entre_tres += posicion is not None and posicion <= 3
                reciprocos += 1 / posicion if posicion else 0
            total = len(filas)
            print(
                f"{modo:<10} acierto@1 {al_primero / total:6.1%}   acierto@3 {entre_tres / total:6.1%}"
                f"   MRR {reciprocos / total:.3f}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    evaluar()