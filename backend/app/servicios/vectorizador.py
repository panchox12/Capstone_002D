"""Servicio para calcular representaciones vectoriales (embeddings) de textos."""

from functools import lru_cache


@lru_cache(maxsize=1)
def _obtener_modelo():
    """Carga perezosa del modelo sentence-transformers para evitar retrasar el inicio de la app."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        return None


def vectorizar_texto(texto: str) -> list[float]:
    """Genera un vector unitario de 384 dimensiones a partir de un texto.

    Si sentence-transformers no esta instalado, genera un embedding determinista
    normalizado para pruebas y entornos ligeros.
    """
    texto_limpio = texto.strip().lower()
    modelo = _obtener_modelo()

    if modelo is not None:
        vector = modelo.encode(texto_limpio, normalize_embeddings=True)
        return vector.tolist()

    # Fallback determinista en 384 dimensiones para pruebas y entornos sin el modelo pesado
    import hashlib

    hash_bytes = hashlib.sha256(texto_limpio.encode("utf-8")).digest()
    vector = [0.0] * 384
    for idx, b in enumerate(hash_bytes):
        vector[idx % 384] += float(b) / 255.0

    # Normalizar L2 para distancia coseno
    norma = sum(x**2 for x in vector) ** 0.5
    if norma > 0:
        vector = [x / norma for x in vector]

    return vector