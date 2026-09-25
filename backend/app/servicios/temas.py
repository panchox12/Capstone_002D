"""Catalogo de temas: creacion con nivel calculado y arbol completo."""
 
from sqlalchemy import select
from sqlalchemy.orm import Session
 
from app.modelos.tema import NIVEL_MAXIMO, EstadoTema, Tema
 
 
class TemaNoExiste(Exception):
    """El tema padre indicado no existe."""
 
 
class NivelMaximoAlcanzado(Exception):
    """Se intento crear un tema superando el ultimo nivel."""
 
 
def crear(
    db: Session,
    nombre: str,
    tema_padre_id: int | None = None,
    descripcion: str | None = None,
) -> Tema:
    """Crea un tema. El nivel no se recibe: se calcula a partir del padre."""
    nivel = 1
    if tema_padre_id is not None:
        padre = db.get(Tema, tema_padre_id)
        if padre is None:
            raise TemaNoExiste()
        if padre.nivel >= NIVEL_MAXIMO:
            raise NivelMaximoAlcanzado()
        nivel = padre.nivel + 1
 
    tema = Tema(nombre=nombre.strip(), tema_padre_id=tema_padre_id, nivel=nivel, descripcion=descripcion)
    db.add(tema)
    db.flush()
    return tema
 
 
def obtener_o_crear(db: Session, nombre: str, tema_padre_id: int | None = None) -> Tema:
    """Devuelve el tema si ya existe con ese nombre bajo ese padre; si no, lo crea.
 
    Permite correr el semillero varias veces sin duplicar nada.
    """
    condicion_padre = Tema.tema_padre_id.is_(None) if tema_padre_id is None else Tema.tema_padre_id == tema_padre_id
    existente = db.execute(select(Tema).where(Tema.nombre == nombre, condicion_padre)).scalar_one_or_none()
    if existente is not None:
        return existente
    return crear(db, nombre, tema_padre_id)
 
 
def arbol(db: Session) -> list[dict]:
    """Todos los temas activos, anidados: cada uno con la lista de sus hijos.
 
    Si un tema esta inactivo, sus hijos tampoco aparecen, aunque esten activos:
    quedan sin padre donde colgarse.
    """
    temas = db.execute(
        select(Tema).where(Tema.estado == EstadoTema.ACTIVO).order_by(Tema.nivel, Tema.nombre)
    ).scalars().all()
 
    nodos = {
        tema.id: {"id": tema.id, "nombre": tema.nombre, "nivel": tema.nivel, "descripcion": tema.descripcion, "hijos": []}
        for tema in temas
    }
    raices = []
    for tema in temas:
        if tema.tema_padre_id is None:
            raices.append(nodos[tema.id])
        elif tema.tema_padre_id in nodos:
            nodos[tema.tema_padre_id]["hijos"].append(nodos[tema.id])
    return raices