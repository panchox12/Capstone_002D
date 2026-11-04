"""Le da a una cuenta el rol de soporte o de administrador, o se lo quita.

Uso, desde la carpeta backend:
    python -m scripts.asignar_rol correo@ejemplo.cl soporte
    python -m scripts.asignar_rol correo@ejemplo.cl administrador
    python -m scripts.asignar_rol correo@ejemplo.cl usuario
"""

import sys

from sqlalchemy import select

from app.db.sesion import SesionLocal
from app.modelos.usuario import RolUsuario, Usuario


def asignar(correo: str, rol: str) -> str:
    try:
        nuevo = RolUsuario(rol)
    except ValueError:
        opciones = ", ".join(miembro.value for miembro in RolUsuario)
        return f"Rol desconocido. Usa uno de estos: {opciones}"
    db = SesionLocal()
    try:
        usuario = db.execute(select(Usuario).where(Usuario.correo == correo.strip().lower())).scalar_one_or_none()
        if usuario is None:
            return f"No existe una cuenta con el correo {correo}"
        usuario.rol = nuevo
        db.commit()
        return f"{usuario.correo} ahora tiene el rol {nuevo.value}"
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    print(asignar(sys.argv[1], sys.argv[2]))