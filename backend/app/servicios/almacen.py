"""Acceso al bucket de grabaciones en S3.

Solo hace dos cosas: un enlace temporal para que soporte vea una grabacion,
y borrar el archivo cuando vence. Las pruebas lo reemplazan por uno falso.
"""

from functools import lru_cache

import boto3

from app.core.config import configuracion

# El enlace para ver una grabacion dura poco: solo para abrirla en ese momento.
SEGUNDOS_ENLACE = 600


class AlmacenS3:
    def __init__(self, cliente, bucket: str):
        self.cliente = cliente
        self.bucket = bucket

    def enlace_temporal(self, clave: str) -> str:
        return self.cliente.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": clave}, ExpiresIn=SEGUNDOS_ENLACE
        )

    def borrar(self, clave: str) -> None:
        # S3 no avisa error si el archivo ya no estaba.
        self.cliente.delete_object(Bucket=self.bucket, Key=clave)


@lru_cache
def obtener_almacen() -> AlmacenS3:
    llaves = {}
    if configuracion.aws_access_key_id:
        llaves = {
            "aws_access_key_id": configuracion.aws_access_key_id,
            "aws_secret_access_key": configuracion.aws_secret_access_key,
        }
    cliente = boto3.client("s3", region_name=configuracion.aws_region, **llaves)
    return AlmacenS3(cliente, configuracion.grabacion_bucket)