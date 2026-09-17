# Convenciones del proyecto Cachai

## Commits

Se usa el estandar Conventional Commits:

    <tipo>(<alcance>): <descripcion en minusculas y en presente>

### Tipos permitidos

| Tipo | Cuando se usa |
|---|---|
| feat | Funcionalidad nueva |
| fix | Correccion de un error |
| docs | Solo documentacion |
| test | Agregar o corregir pruebas |
| refactor | Cambio interno sin alterar comportamiento |
| chore | Configuracion, dependencias, estructura |
| style | Formato, sin cambio de logica |

### Alcances del proyecto

auth, tokens, solicitudes, sesion, cobro, busqueda, grabacion,
moderacion, admin, infra, db

### Ejemplos

    feat(tokens): motor de consumo por lotes con FOR UPDATE
    fix(cobro): el cronometro no se detenia en la tercera pausa
    docs: diario de reflexion fase 2

## Ramas

- main: siempre debe estar funcionando
- feature/<nombre>: una rama por funcionalidad

Flujo:

    git checkout -b feature/motor-tokens
    ... trabajar y commitear ...
    git checkout main
    git pull
    git merge feature/motor-tokens
    git push

## Reglas del equipo

1. No se commitea codigo que no compila o no arranca
2. No se commitea el archivo .env
3. Antes de empezar a trabajar, siempre: git pull
4. Cada fase del plan termina con al menos un commit
5. Los mensajes de commit se escriben en espanol sin acentos