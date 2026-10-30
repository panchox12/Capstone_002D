"""Buscador de especialistas: por palabras (lexico) o por significado (semantico).

Los dos modos hacen lo mismo en dos pasos: primero encuentran los temas del
catalogo que corresponden a la duda, y despues las habilidades publicadas en
esos temas. Asi se pueden comparar en la validacion experimental.
"""

import enum
import uuid

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos.embedding import EmbeddingTema
from app.modelos.habilidad import EstadoHabilidad, HabilidadOfrecida
from app.modelos.perfil import PerfilPublico
from app.modelos.tema import NIVEL_MAXIMO, EstadoTema, Tema
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import embeddings, parametros, presencia

PARAM_MIN_ESTRELLAS = "sesiones_minimas_para_estrellas"

# Similitud minima (de 0 a 1) para que un tema cuente; se calibro con scripts.evaluar_buscador.
UMBRAL_SIMILITUD = 0.20
TEMAS_SEMANTICOS = 5

# Palabras que no ayudan a encontrar un tema.
PALABRAS_VACIAS = {
    "como", "con", "del", "las", "los", "mas", "para", "por", "que", "una", "uno", "unos", "unas",
    "tengo", "necesito", "ayuda", "problema", "duda", "quiero", "saber", "esta", "este", "esto", "mi", "mis",
}


class Modo(str, enum.Enum):
    LEXICO = "lexico"
    SEMANTICO = "semantico"


# ---------------------------------------------------------------------------
# Temas del catalogo con su ruta
# ---------------------------------------------------------------------------


def temas_ofrecibles(db: Session) -> list[tuple[Tema, str]]:
    # Temas activos de nivel 3 con la ruta de sus padres, por ejemplo "Oficios > Electricidad".
    activos = {tema.id: tema for tema in db.execute(select(Tema).where(Tema.estado == EstadoTema.ACTIVO)).scalars()}
    resultado = []
    for tema in activos.values():
        if tema.nivel != NIVEL_MAXIMO:
            continue
        padre = activos.get(tema.tema_padre_id)
        abuelo = activos.get(padre.tema_padre_id) if padre else None
        # Si un padre esta inactivo, el tema tampoco se ofrece.
        if padre is None or abuelo is None:
            continue
        resultado.append((tema, f"{abuelo.nombre} > {padre.nombre}"))
    return resultado


def texto_de_tema(tema: Tema, ruta: str) -> str:
    return f"{tema.nombre}. {ruta.replace(' > ', '. ')}. {tema.descripcion or ''}".strip()


def calcular_embeddings(db: Session) -> int:
    # Calcula el vector de cada tema nuevo o cambiado. Devuelve cuantos calculo.
    modelo = embeddings.nombre_modelo()
    pendientes = []
    for tema, ruta in temas_ofrecibles(db):
        texto = texto_de_tema(tema, ruta)
        actual = db.get(EmbeddingTema, tema.id)
        if actual is None or actual.texto != texto or actual.modelo != modelo:
            pendientes.append((tema.id, texto, actual))

    vectores = embeddings.vectorizar([texto for _, texto, _ in pendientes]) if pendientes else []
    for (tema_id, texto, actual), vector in zip(pendientes, vectores):
        if actual is None:
            db.add(EmbeddingTema(tema_id=tema_id, vector=vector, modelo=modelo, texto=texto))
        else:
            actual.vector, actual.modelo, actual.texto = vector, modelo, texto
    db.flush()
    return len(pendientes)


# ---------------------------------------------------------------------------
# Paso 1: de la duda a los temas
# ---------------------------------------------------------------------------


def _palabras(consulta: str) -> set[str]:
    return {
        palabra for palabra in embeddings.normalizar(consulta).split()
        if len(palabra) >= 3 and palabra not in PALABRAS_VACIAS
    }


def temas_lexicos(db: Session, consulta: str) -> list[tuple[int, float]]:
    # Temas cuyo nombre o ruta contiene las palabras de la duda, con la fraccion que coincidio.
    palabras = _palabras(consulta)
    if not palabras:
        return []
    resultado = []
    for tema, ruta in temas_ofrecibles(db):
        texto = embeddings.normalizar(texto_de_tema(tema, ruta))
        coincidencias = sum(1 for palabra in palabras if palabra in texto)
        if coincidencias:
            resultado.append((tema.id, coincidencias / len(palabras)))
    return sorted(resultado, key=lambda par: par[1], reverse=True)


def hay_embeddings(db: Session) -> bool:
    return db.scalar(select(func.count()).select_from(EmbeddingTema)) > 0


def temas_semanticos(db: Session, consulta: str) -> list[tuple[int, float]]:
    # Temas cuyo vector mas se parece al de la duda, con su similitud de 0 a 1.
    vector = embeddings.vectorizar([consulta])[0]
    distancia = EmbeddingTema.vector.cosine_distance(vector)
    filas = db.execute(
        select(EmbeddingTema.tema_id, distancia)
        .where(EmbeddingTema.modelo == embeddings.nombre_modelo())
        .order_by(distancia)
        .limit(TEMAS_SEMANTICOS)
    ).all()
    return [(tema_id, round(1 - dist, 4)) for tema_id, dist in filas if 1 - dist >= UMBRAL_SIMILITUD]


# ---------------------------------------------------------------------------
# Paso 2: de los temas a las habilidades
# ---------------------------------------------------------------------------


def buscar(
    db: Session,
    r: redis.Redis,
    usuario_id: uuid.UUID,
    consulta: str,
    modo: Modo,
    solo_en_linea: bool = False,
    limite: int = 20,
) -> tuple[Modo, list[dict]]:
    # Sin vectores calculados, el modo semantico no puede responder: se usa el lexico.
    if modo == Modo.SEMANTICO and not hay_embeddings(db):
        modo = Modo.LEXICO
    puntajes = dict(temas_semanticos(db, consulta) if modo == Modo.SEMANTICO else temas_lexicos(db, consulta))
    if not puntajes:
        return modo, []

    filas = db.execute(
        select(HabilidadOfrecida, Tema, Usuario, PerfilPublico)
        .join(Tema, Tema.id == HabilidadOfrecida.tema_id)
        .join(Usuario, Usuario.id == HabilidadOfrecida.usuario_id)
        .outerjoin(PerfilPublico, PerfilPublico.usuario_id == Usuario.id)
        .where(
            HabilidadOfrecida.tema_id.in_(puntajes),
            HabilidadOfrecida.estado == EstadoHabilidad.PUBLICADA,
            Usuario.estado_cuenta == EstadoCuenta.ACTIVA,
            Usuario.id != usuario_id,
        )
    ).all()

    conectados = presencia.en_linea(r, [usuario.id for _, _, usuario, _ in filas])
    min_estrellas = parametros.obtener_entero(db, PARAM_MIN_ESTRELLAS)
    rutas = dict((tema.id, ruta) for tema, ruta in temas_ofrecibles(db))

    resultados = []
    for habilidad, tema, usuario, perfil in filas:
        en_linea = usuario.id in conectados
        if solo_en_linea and not en_linea:
            continue
        evaluaciones = perfil.total_evaluaciones if perfil else 0
        # El promedio se muestra recien desde el minimo de valoraciones.
        reputacion = float(perfil.reputacion_promedio) if perfil and evaluaciones >= min_estrellas else None
        resultados.append(
            {
                "habilidad_id": habilidad.id,
                "tema_id": tema.id,
                "tema_nombre": tema.nombre,
                "ruta": rutas.get(tema.id, ""),
                "puntaje": puntajes[tema.id],
                "precio_por_bloque": habilidad.precio_por_bloque,
                "tutor_id": usuario.id,
                "tutor_nombre": usuario.nombre_visible,
                "reputacion_promedio": reputacion,
                "total_evaluaciones": evaluaciones,
                "en_linea": en_linea,
            }
        )

    # Primero el tema mas pertinente, despues la mejor reputacion y al final el precio mas bajo.
    resultados.sort(key=lambda fila: (-fila["puntaje"], -(fila["reputacion_promedio"] or 0), fila["precio_por_bloque"]))
    return modo, resultados[:limite]