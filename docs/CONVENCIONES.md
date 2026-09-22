# Convenciones del proyecto Cachai

## Commits

Formato (Conventional Commits):

    <tipo>(<alcance>): <descripcion en minusculas y en presente>

### Tipos

| Tipo | Cuando se usa |
|---|---|
| feat | Funcionalidad nueva |
| fix | Correccion de un error |
| docs | Solo documentacion |
| test | Agregar o corregir pruebas |
| refactor | Cambio interno sin alterar comportamiento |
| chore | Configuracion, dependencias, estructura |
| style | Formato, sin cambio de logica |

### Alcances

auth, identidad, perfiles, tokens, solicitudes, sesion, cobro, busqueda,
grabacion, moderacion, admin, frontend, infra, db

### Ejemplos

    feat(tokens): motor de consumo por lotes con FOR UPDATE
    fix(cobro): el cronometro no se detenia en la tercera pausa
    docs: acta del sprint 3

## Ramas

`main` siempre funciona. Todo trabajo nuevo nace en una rama y vuelve a
`main` solo mediante un pull request revisado por el otro integrante.
Nada se sube directo a `main`.

### Nombres

| Prefijo | Uso | Ejemplo |
|---|---|---|
| feature/ | Funcionalidad nueva | feature/motor-consumo-tokens |
| fix/ | Correccion de un error | fix/cronometro-tercera-pausa |
| docs/ | Documentacion o entregables | docs/acta-sprint-3 |
| chore/ | Configuracion o estructura | chore/base-datos-pruebas |

Minusculas, guiones y sin tildes. Una rama dura entre uno y tres dias.

### Flujo

    git checkout main
    git pull
    git checkout -b feature/nombre
    # ... commits ...
    git push -u origin feature/nombre
    # abrir el pull request en GitHub y pedir revision

Si `main` avanza mientras trabajas:

    git checkout main
    git pull
    git checkout feature/nombre
    git merge main

Al integrar se usa siempre **Create a merge commit**. Despues:

    git checkout main
    git pull
    git branch -d feature/nombre

## Pull requests

- Titulo con el mismo formato de los commits.
- La descripcion sigue la plantilla del repositorio.
- Se revisan el mismo dia en que se abren.
- Solo se integran si cumplen la Definicion de Terminado.

## Definicion de Terminado

1. Integrado a `main` mediante pull request revisado por el otro integrante
2. Las pruebas pasan y la funcionalidad nueva tiene sus propias pruebas
3. Toda migracion es reversible y `alembic heads` muestra una sola cabeza
4. El repositorio no contiene credenciales ni datos personales
5. Cumple los criterios de aceptacion definidos por el Product Owner
6. Se puede demostrar funcionando en la revision del sprint

## Reglas del equipo

1. `git pull` antes de empezar a trabajar
2. `git pull` y `git merge main` antes de generar una migracion
3. Avisar al modificar archivos compartidos: `app/main.py`,
   `app/modelos/__init__.py`, `app/core/config.py`, `tests/conftest.py`
4. Avisar cuando cambie `.env.example` o `requirements.lock.txt`
5. No construir sobre una rama sin integrar del otro integrante
6. No se commitea el archivo `.env`
7. Mensajes de commit en espanol sin acentos
8. Cada sprint cierra con la etiqueta `sprint-N` sobre `main`