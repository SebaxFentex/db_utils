"""Test local de construccion de engines, sin conectarse a ninguna base.

Verifica la URL que se arma (servicio, puerto, opciones extra), que la clave
nunca quede visible y que construir un engine no abra conexiones.

Uso: uv run python tests/test_crear_engines.py
"""

from __future__ import annotations

import logging

from db_utils import (
    ExcepcionConexion,
    crear_engine_oracle,
    crear_engine_sqlserver,
    inicializar_cliente_oracle,
)
from sqlalchemy.pool import QueuePool

from db_utils._log import configurar_log

log = logging.getLogger("db_utils.tests")


def _probar_oracle() -> None:
    engine = crear_engine_oracle(
        usuario="usuario_prueba",
        clave="clave_secreta",
        host="servidor.local",
        servicio="SERVICIO",
    )
    url = engine.url.render_as_string(hide_password=True)
    assert "oracle+oracledb" in url, f"driver inesperado: {url}"
    assert "servidor.local:1521" in url, f"puerto por defecto ausente: {url}"
    assert "service_name=SERVICIO" in url, f"service_name ausente: {url}"
    assert "clave_secreta" not in url, f"la clave quedo visible: {url}"
    assert isinstance(engine.pool, QueuePool), f"pool inesperado: {type(engine.pool).__name__}"
    assert engine.pool.checkedout() == 0, "construir el engine abrio una conexion"
    log.info("OK engine Oracle: %s", url)

    con_puerto = crear_engine_oracle(
        usuario="u", clave="c", host="h", servicio="S", puerto=1522, query={"modo": "prueba"}
    )
    assert con_puerto.url.port == 1522, f"puerto {con_puerto.url.port}"
    assert con_puerto.url.query.get("modo") == "prueba", f"opciones: {con_puerto.url.query}"
    log.info("OK engine Oracle con puerto y opciones extra")


def _probar_sqlserver() -> None:
    engine = crear_engine_sqlserver(
        usuario="usuario_prueba",
        clave="clave_secreta",
        host="servidor.local",
        base_datos="BASE",
        query={"tds_version": "7.0"},
    )
    url = engine.url.render_as_string(hide_password=True)
    assert "mssql+pymssql" in url, f"driver inesperado: {url}"
    assert "servidor.local/BASE" in url, f"base ausente: {url}"
    assert "clave_secreta" not in url, f"la clave quedo visible: {url}"
    assert engine.url.query.get("tds_version") == "7.0", f"tds: {engine.url.query}"
    assert isinstance(engine.pool, QueuePool), f"pool inesperado: {type(engine.pool).__name__}"
    assert engine.pool.checkedout() == 0, "construir el engine abrio una conexion"
    log.info("OK engine SQL Server con tds_version por parametro: %s", url)

    sin_opciones = crear_engine_sqlserver(
        usuario="u", clave="c", host="h", base_datos="B", puerto=1433
    )
    assert sin_opciones.url.port == 1433, f"puerto {sin_opciones.url.port}"
    assert not sin_opciones.url.query, f"query inesperada: {sin_opciones.url.query}"
    log.info("OK engine SQL Server con puerto y sin opciones")


def _probar_validaciones() -> None:
    casos = (
        ("usuario vacio", lambda: crear_engine_oracle("", "c", "h", "s")),
        ("host vacio", lambda: crear_engine_oracle("u", "c", "  ", "s")),
        ("puerto invalido", lambda: crear_engine_oracle("u", "c", "h", "s", puerto=0)),
        ("base vacia", lambda: crear_engine_sqlserver("u", "c", "h", " ")),
        ("puerto sqlserver invalido", lambda: crear_engine_sqlserver("u", "c", "h", "b", puerto=70000)),
    )
    for descripcion, llamada in casos:
        try:
            llamada()
        except ValueError:
            continue
        raise AssertionError(f"{descripcion} deberia lanzar ValueError")
    log.info("OK validacion de parametros como ValueError nativo")

    casos_tipo = (
        ("usuario None", lambda: crear_engine_oracle(None, "c", "h", "s")),  # ty: ignore[invalid-argument-type]
        ("base None", lambda: crear_engine_sqlserver("u", "c", "h", None)),  # ty: ignore[invalid-argument-type]
    )
    for descripcion, llamada in casos_tipo:
        try:
            llamada()
        except TypeError:
            continue
        raise AssertionError(f"{descripcion} deberia lanzar TypeError")
    log.info("OK parametros que no son texto como TypeError nativo")


def _probar_cliente_oracle() -> None:
    try:
        inicializar_cliente_oracle("C:/ruta/que/no/tiene/oracle/client")
    except ExcepcionConexion as exc:
        assert exc.codigo_salida == 2, f"codigo de salida {exc.codigo_salida}"
        log.info("OK cliente Oracle inexistente traducido a codigo 2")
    else:
        raise AssertionError("una ruta sin Oracle Client no lanzo ExcepcionConexion")

    try:
        inicializar_cliente_oracle("")
    except ValueError:
        log.info("OK ruta vacia como ValueError nativo")
    else:
        raise AssertionError("una ruta vacia deberia lanzar ValueError")


def main() -> None:
    configurar_log()
    log.info("Test de construccion de engines")

    _probar_oracle()
    _probar_sqlserver()
    _probar_validaciones()
    _probar_cliente_oracle()

    log.info("OK test_crear_engines completo")


if __name__ == "__main__":
    main()
