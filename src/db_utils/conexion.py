"""Construccion de engines de SQLAlchemy a partir de parametros explicitos.

Las credenciales y opciones llegan como parametros. La conexion se abre en el
primer uso: ``ejecutar_sql`` traduce el fallo a ``ExcepcionConexion``.
"""

from __future__ import annotations

import logging

import oracledb
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from ._excepciones import ExcepcionConexion

log = logging.getLogger(__name__)


def crear_engine_oracle(
    usuario: str,
    clave: str,
    host: str,
    servicio: str,
    puerto: int = 1521,
    query: dict[str, str] | None = None,
) -> Engine:
    """Crea un engine de Oracle.

    Args:
        usuario: usuario de la base.
        clave: clave del usuario.
        host: nombre o IP del servidor.
        servicio: service name al que se conecta.
        puerto: puerto del listener (por defecto 1521).
        query: opciones extra para la URL, por ejemplo
            ``{"ssl_server_dn_match": "false"}``.

    Returns:
        Engine de SQLAlchemy configurado con verificacion de conexion previa.

    Raises:
        TypeError: si un parametro obligatorio no es texto.
        ValueError: si un parametro obligatorio llega vacio o el puerto no es valido.
    """
    usuario = _verificar_parametro_obligatorio(usuario, "usuario")
    clave = _verificar_parametro_obligatorio(clave, "clave")
    host = _verificar_parametro_obligatorio(host, "host")
    servicio = _verificar_parametro_obligatorio(servicio, "servicio")
    if not isinstance(puerto, int) or puerto <= 0 or puerto > 65535:
        raise ValueError(f"El puerto de Oracle no es valido: {puerto!r}")

    opciones = {"service_name": servicio}
    if query:
        opciones.update({str(k): str(v) for k, v in query.items()})

    url = URL.create(
        drivername="oracle+oracledb",
        username=usuario,
        password=clave,
        host=host,
        port=puerto,
        query=opciones,
    )
    log.debug("Engine Oracle construido para %s:%s/%s", host, puerto, servicio)
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


def crear_engine_sqlserver(
    usuario: str,
    clave: str,
    host: str,
    base_datos: str,
    puerto: int | None = None,
    query: dict[str, str] | None = None,
) -> Engine:
    """Crea un engine de SQL Server con el driver ``pymssql``.

    Args:
        usuario: usuario de la base.
        clave: clave del usuario.
        host: nombre o IP del servidor.
        base_datos: base a la que se conecta.
        puerto: puerto del servidor; ``None`` usa el default del driver.
        query: opciones extra para la URL, por ejemplo
            ``{"tds_version": "7.0"}`` para servidores que solo hablan TDS 7.0.

    Returns:
        Engine de SQLAlchemy configurado con verificacion de conexion previa.

    Raises:
        TypeError: si un parametro obligatorio no es texto.
        ValueError: si un parametro obligatorio llega vacio o el puerto no es valido.
    """
    usuario = _verificar_parametro_obligatorio(usuario, "usuario")
    clave = _verificar_parametro_obligatorio(clave, "clave")
    host = _verificar_parametro_obligatorio(host, "host")
    base_datos = _verificar_parametro_obligatorio(base_datos, "base_datos")
    if puerto is not None and (not isinstance(puerto, int) or puerto <= 0 or puerto > 65535):
        raise ValueError(f"El puerto de SQL Server no es valido: {puerto!r}")

    url = URL.create(
        drivername="mssql+pymssql",
        username=usuario,
        password=clave,
        host=host,
        port=puerto,
        database=base_datos,
        query={str(k): str(v) for k, v in (query or {}).items()},
    )
    log.debug("Engine SQL Server construido para %s/%s", host, base_datos)
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


def inicializar_cliente_oracle(ruta_cliente: str) -> None:
    """Inicializa Oracle Client en modo thick.

    Debe llamarse antes de abrir cualquier conexion.

    Args:
        ruta_cliente: carpeta donde esta el Oracle Client de 64 bits.

    Raises:
        TypeError: si ``ruta_cliente`` no es texto.
        ValueError: si ``ruta_cliente`` llega vacia.
        ExcepcionConexion: si la ruta no contiene un cliente utilizable o si el
            proceso ya abrio una conexion en modo thin.

    Notes:
        Sin esta llamada ``oracledb`` trabaja en modo thin; se usa cuando la
        conexion depende de un Oracle Client instalado (TNS, NLS). La
        idempotencia y el rechazo del cambio de modo los aplica ``oracledb``:
        repetir con la misma ruta no tiene efecto y con otra ruta falla.
    """
    ruta = _verificar_parametro_obligatorio(ruta_cliente, "ruta_cliente")

    try:
        oracledb.init_oracle_client(lib_dir=ruta)
    except oracledb.Error as exc:
        raise ExcepcionConexion(
            f"No se pudo inicializar Oracle Client en '{ruta}': {exc}"
        ) from exc

    log.info("Oracle Client inicializado en %s", ruta)


def _verificar_parametro_obligatorio(valor: object, nombre: str) -> str:
    """Devuelve el valor sin espacios sobrantes, o corta con la excepcion nativa.

    La entrada se anota ``object`` a proposito: la funcion existe para verificar
    que lo recibido sea texto, asi que no puede dar por hecho que ya lo es.

    Raises:
        TypeError: si el valor no es texto (``None``, un numero, una lista).
        ValueError: si el valor es texto pero quedo vacio o solo con espacios.
    """
    if not isinstance(valor, str):
        raise TypeError(
            f"El parametro '{nombre}' debe ser texto, llego {type(valor).__name__}"
        )

    limpio = valor.strip()
    if not limpio:
        raise ValueError(f"El parametro '{nombre}' es obligatorio y no puede estar vacio")
    return limpio
