"""Excepciones propias de la libreria db.

El codigo de salida viaja como atributo de clase para que el proyecto
consumidor haga ``sys.exit(exc.codigo_salida)`` sin repetir el numero.

Tabla de codigos de la libreria:

    0  ejecucion correcta (universal)
    1  fallo generico (convencion Python)
    2  no se pudo conectar con la base de datos
    3  la base rechazo una sentencia SQL

Los datos de entrada malformados llegan como ``TypeError`` (tipo incorrecto) o
``ValueError`` (texto vacio), sin envolverse.
"""


class ExcepcionDb(Exception):
    """Base de los errores propios de la libreria (fallo generico)."""

    codigo_salida = 1


class ExcepcionConexion(ExcepcionDb):
    """No se pudo preparar o mantener la conexion con la base de datos."""

    codigo_salida = 2


class ExcepcionEjecucionSql(ExcepcionDb):
    """La base de datos respondio con error a una sentencia enviada."""

    codigo_salida = 3
