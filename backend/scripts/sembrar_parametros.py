"""Carga los valores iniciales de los parametros configurables.

Se ejecuta una sola vez, o cada vez que se agregue un parametro nuevo
a la lista de abajo.
"""

from app.db.sesion import SesionLocal
from app.modelos.parametro import ParametroSistema

PARAMETROS_INICIALES = [
    ("tokens_gratis_semanales", "10", "Tokens gratis que se entregan cada semana"),
    ("tope_saldo_gratis", "10", "Tope maximo del saldo gratuito"),
    ("dias_vencimiento_gratis", "7", "Dias antes de que venza un token gratis"),
    ("tokens_por_video", "1", "Tokens ganados por video publicitario visto"),
    ("tope_videos_por_dia", "3", "Tope de videos vistos cada 24 horas"),
    ("dias_vencimiento_comprado", "30", "Dias antes de que venza un token comprado"),
    ("dias_vencimiento_enseñado", "15", "Dias antes de que venza un token recibido por enseñar"),
    ("duracion_bloque_minutos", "15", "Duracion del bloque de consulta"),
    ("ventana_respuesta_solicitud_minutos", "5", "Minutos para aceptar o rechazar una solicitud"),
    ("ventana_conexion_sala_minutos", "5", "Minutos para que ambos se conecten a la sala"),
    ("tiempo_reconexion_segundos", "90", "Segundos otorgados para reconectar tras una caida"),
    ("pausas_maximas_por_sesion", "3", "Pausas maximas permitidas por sesion"),
    ("retencion_posterior_sesion_minutos", "10", "Minutos que se retienen los tokens tras la sesion"),
    ("plazo_reporte_horas", "48", "Horas para reportar una sesion"),
    ("retencion_grabaciones_horas", "24", "Horas de retencion de las grabaciones"),
    ("sesiones_minimas_para_estrellas", "5", "Sesiones valoradas minimas para mostrar el promedio"),
    ("precio_maximo_bloque", "0", "Precio maximo por bloque. 0 significa sin limite activo"),
]


def sembrar():
    db = SesionLocal()
    creados = 0
    try:
        for nombre, valor, descripcion in PARAMETROS_INICIALES:
            existente = db.get(ParametroSistema, nombre)
            if existente is None:
                db.add(ParametroSistema(nombre=nombre, valor=valor, descripcion=descripcion))
                creados += 1
        db.commit()
        print(f"Parametros creados: {creados}")
    finally:
        db.close()


if __name__ == "__main__":
    sembrar()