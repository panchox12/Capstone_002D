# Cachai

Plataforma web de microconsultas en vivo. Una persona con una duda concreta se conecta por videollamada con alguien que sabe del tema y le paga con tokens, en bloques de quince minutos. Los tokens se compran o se ganan ayudando a otros, y nunca salen de la plataforma como dinero.

Proyecto de titulo de Ingenieria en Informatica, Duoc UC (Capstone APT122, 2026).

Equipo: Carlos Meza (Product Owner) y Francisco Bascour (Scrum Master). Los dos desarrollamos.

## Tecnologias

- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Base de datos: PostgreSQL con pgvector y Redis
- Frontend: React, Vite y Tailwind CSS
- Videollamada: LiveKit
- Nube: AWS (EC2 con Docker, RDS, S3, CloudFront, SES y Rekognition)
- Pruebas: pytest y Vitest

La API tiene toda la logica de negocio y la contabilidad de tokens. El navegador nunca informa tiempos ni montos: el cobro de cada bloque lo calcula el servidor con los avisos que envia LiveKit. El detalle esta en el Documento de Diseno y en el Manual Tecnico, dentro de `docs/entregables`.

## Requisitos

Git, Docker Desktop, Python 3.12 o superior y Node.js 22.12 o superior.

## Como levantarlo

Desde la carpeta del proyecto, levantar PostgreSQL y Redis:

```
docker compose up -d
```

Backend:

```
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

En `backend\.env` hay que reemplazar `SECRET_KEY` y `SAL_DOCUMENTO` por dos claves distintas. Cada una se genera con:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

Luego crear las tablas, cargar los datos iniciales y levantar la API:

```
alembic upgrade head
python -m scripts.sembrar_parametros
python -m scripts.sembrar_temas
python -m scripts.calcular_embeddings
python -m uvicorn app.main:app --reload
```

`calcular_embeddings` prepara el buscador por significado; la primera vez descarga el modelo, asi que demora un poco. La documentacion de la API queda en http://localhost:8000/docs. En desarrollo no se envian correos: el enlace para confirmar una cuenta aparece en la terminal de uvicorn.

Frontend, en otra terminal:

```
cd frontend
npm install
npm run dev
```

La aplicacion queda en http://localhost:5173.

Para entrar a las secciones de soporte o de administracion hay que darle el rol a la cuenta, desde `backend`:

```
python -m scripts.asignar_rol correo@ejemplo.cl soporte
```

## Pruebas

```
cd backend
python -m pytest

cd ..\frontend
npm test
npm run lint
```

Las pruebas del backend necesitan Docker encendido. Usan una base de datos aparte llamada `cachai_test`, que se crea sola.

## Forma de trabajo

Cada cambio se hace en una rama y llega a `main` solo mediante un pull request revisado por el otro integrante. Las reglas de ramas y commits estan en `docs/CONVENCIONES.md`.

## Despliegue

El sistema esta desplegado en AWS. Los pasos para instalarlo y actualizarlo estan en el Manual Tecnico.
