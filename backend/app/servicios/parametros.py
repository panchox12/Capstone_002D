"""Lectura de parametros configurables desde la base de datos."""

from sqlalchemy.orm import Session

from app.modelos.parametro import ParametroSistema


#Devuelve el valor de un parametro como texto. Lanza un error si el parametro no existe
def obtener(db: Session, nombre: str) -> str:
    parametro = db.get(ParametroSistema, nombre)
    if parametro is None:
        raise ValueError(f"El parametro '{nombre}' no existe en la base de datos")
    return parametro.valor


def obtener_entero(db: Session, nombre: str) -> int:
    return int(obtener(db, nombre))