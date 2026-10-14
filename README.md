# Cachai

Plataforma web de microconsultas en vivo. Una persona con una duda concreta se conecta por videollamada con alguien que sabe del tema y le paga con tokens, en bloques de quince minutos. Los tokens se compran o se ganan ayudando a otros, y nunca salen de la plataforma como dinero.

Proyecto de titulo de Ingenieria en Informatica, Duoc UC (Capstone APT122, 2026).

Equipo: Carlos Meza (Product Owner) y Francisco Bascour (Scrum Master).

## Tecnologias

- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Base de datos: PostgreSQL y Redis
- Frontend: React, Vite y Tailwind CSS
- Pruebas: pytest y Vitest

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
uvicorn app.main:app --reload
```

La documentacion de la API queda en http://localhost:8000/docs. En desarrollo no se envian correos: el enlace para confirmar una cuenta aparece en la terminal de uvicorn.

Frontend, en otra terminal:

```
cd frontend
npm install
npm run dev
```

La aplicacion queda en http://localhost:5173.

## Pruebas

```
cd backend
pytest

cd ..\frontend
npm test
```

Las pruebas del backend necesitan Docker encendido. Usan una base de datos aparte llamada `cachai_test`, que se crea sola.

## Forma de trabajo

Cada cambio se hace en una rama y llega a `main` solo mediante un pull request revisado por el otro integrante. Las reglas de ramas y commits estan en `docs/CONVENCIONES.md`.
