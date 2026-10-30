"""Convierte textos en vectores para el buscador semantico.

PROVEEDOR_EMBEDDINGS=simulado  -> pruebas: vector por palabras, sin descargar nada
PROVEEDOR_EMBEDDINGS=local     -> modelo multilingue que corre en el mismo servidor
                                  (fastembed), sin costo por consulta ni datos a terceros
"""

import hashlib
import math
import unicodedata
from functools import lru_cache

from app.core.config import configuracion
from app.modelos.embedding import DIMENSIONES

MODELO_LOCAL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODELO_SIMULADO = "simulado-por-palabras"


def normalizar(texto: str) -> str:
    # Minusculas y sin tildes: "Álgebra" y "algebra" quedan iguales.
    sin_tildes = "".join(
        letra for letra in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(letra)
    )
    return "".join(letra if letra.isalnum() else " " for letra in sin_tildes.lower())


def _vector_simulado(texto: str) -> list[float]:
    # Cada palabra suma en una posicion fija: textos con palabras comunes se parecen.
    vector = [0.0] * DIMENSIONES
    for palabra in normalizar(texto).split():
        posicion = int(hashlib.sha256(palabra.encode()).hexdigest(), 16) % DIMENSIONES
        vector[posicion] += 1.0
    largo = math.sqrt(sum(valor * valor for valor in vector)) or 1.0
    return [valor / largo for valor in vector]


@lru_cache
def _modelo_local():
    # La primera vez descarga el modelo (unos 220 MB) y lo deja en cache.
    from fastembed import TextEmbedding

    return TextEmbedding(MODELO_LOCAL)


def nombre_modelo() -> str:
    return MODELO_LOCAL if configuracion.proveedor_embeddings == "local" else MODELO_SIMULADO


def vectorizar(textos: list[str]) -> list[list[float]]:
    if configuracion.proveedor_embeddings == "local":
        return [vector.tolist() for vector in _modelo_local().embed(textos)]
    return [_vector_simulado(texto) for texto in textos]