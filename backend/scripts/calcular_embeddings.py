"""Calcula los vectores de los temas del catalogo para el buscador semantico.

Se ejecuta despues de sembrar_temas, y cada vez que cambie el catalogo.
Solo recalcula los temas nuevos o cambiados.
"""

from app.db.sesion import SesionLocal
from app.servicios import embeddings
from app.servicios.buscador import calcular_embeddings


def calcular() -> None:
    db = SesionLocal()
    try:
        cantidad = calcular_embeddings(db)
        db.commit()
        print(f"Temas vectorizados con {embeddings.nombre_modelo()}: {cantidad}")
    finally:
        db.close()


if __name__ == "__main__":
    calcular()