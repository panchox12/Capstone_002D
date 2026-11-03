# Imagen de la API de Cachai para el despliegue en EC2.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/.modelos

WORKDIR /app

# Primero solo las dependencias: si no cambian, Docker reutiliza esta capa y el build es rapido.
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY . .

# La API corre con un usuario sin privilegios, no como root.
RUN useradd --create-home cachai && mkdir -p /app/.modelos && chown -R cachai /app
USER cachai

EXPOSE 8000

# Migra, completa los datos iniciales y levanta un solo proceso: el planificador vive dentro de la API.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.sembrar_parametros && python -m scripts.sembrar_temas && python -m scripts.calcular_embeddings && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*"]