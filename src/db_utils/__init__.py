"""Utilidades para crear engines de SQLAlchemy y ejecutar SQL en Oracle y SQL Server.

La libreria emite logs y el entrypoint los configura: aqui solo se agrega un
``NullHandler`` para no ensuciar la salida de quien importa.

Las credenciales y opciones de cada funcion entran por parametro.
"""

import logging

from ._excepciones import ExcepcionConexion, ExcepcionDb, ExcepcionEjecucionSql
from .conexion import (
    crear_engine_oracle,
    crear_engine_sqlserver,
    inicializar_cliente_oracle,
)
from .ejecucion import SEPARADOR_CONSULTAS, ejecutar_sql

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "SEPARADOR_CONSULTAS",
    "ExcepcionConexion",
    "ExcepcionDb",
    "ExcepcionEjecucionSql",
    "crear_engine_oracle",
    "crear_engine_sqlserver",
    "ejecutar_sql",
    "inicializar_cliente_oracle",
]
