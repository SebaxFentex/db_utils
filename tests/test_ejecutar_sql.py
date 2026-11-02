"""Test local de ejecutar_sql contra sqlite en memoria.

No necesita credenciales ni red: sqlite viene en la biblioteca estandar.
Cubre retorno, parametros ligados, separador, atomicidad y traduccion de errores.

Uso: uv run python tests/test_ejecutar_sql.py
"""

from __future__ import annotations

import io
import logging
from contextlib import redirect_stdout

from sqlalchemy import create_engine, text

from db_utils import (
    SEPARADOR_CONSULTAS,
    ExcepcionConexion,
    ExcepcionEjecucionSql,
    ejecutar_sql,
)
from db_utils._log import configurar_log

log = logging.getLogger("db_utils.tests")


def _crear_engine():
    """Engine sqlite en memoria con la tabla del test."""
    engine = create_engine("sqlite://")
    with engine.begin() as conexion:
        conexion.execute(
            text(
                "create table clientes ("
                "id integer primary key, "
                "nombre text, "
                "ruta text, "
                "activo integer)"
            )
        )
    return engine


def _consultar(engine, sql: str) -> list[tuple]:
    """Lee filas por conexion directa: ejecutar_sql no devuelve datos."""
    with engine.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(sql))]


def _contar(engine) -> int:
    return _consultar(engine, "select count(*) from clientes")[0][0]


def _probar_retorno_y_parametros(engine) -> None:
    retorno = ejecutar_sql(
        "insert into clientes (nombre, ruta, activo) values (:nombre, :ruta, :activo)",
        engine,
        parametros={
            "nombre": "Ana",
            "ruta": "/tmp/ana.txt",
            "activo": True,
            "sobra": "se ignora",
        },
    )
    assert retorno is None, f"ejecutar_sql debe devolver None, devolvio {retorno!r}"

    filas = _consultar(engine, "select nombre, ruta, activo from clientes where nombre = 'Ana'")
    assert filas == [("Ana", "/tmp/ana.txt", 1)], f"fila insertada inesperada: {filas}"
    log.info("OK retorno None, parametros ligados y parametro sobrante ignorado")


def _probar_backslash_intacto(engine) -> None:
    """Regresion: los backslash de una ruta Windows no se corrompen."""
    ruta = r"C:\nuevo\archivo.txt"
    ejecutar_sql(
        "insert into clientes (nombre, ruta) values (:nombre, :ruta)",
        engine,
        parametros={"nombre": "Ruta", "ruta": ruta},
    )
    guardada = _consultar(engine, "select ruta from clientes where nombre = 'Ruta'")[0][0]
    assert guardada == ruta, f"la ruta se corrompio: {guardada!r} != {ruta!r}"
    log.info("OK backslash intacto: %r", guardada)


def _probar_separador(engine) -> None:
    antes = _contar(engine)

    bloque = (
        "insert into clientes (nombre) values ('uno')\n"
        f"{SEPARADOR_CONSULTAS}\n"
        "insert into clientes (nombre) values ('dos')"
    )
    ejecutar_sql(bloque, engine)
    insertadas = _contar(engine) - antes
    assert insertadas == 2, f"se esperaban 2 inserciones, hubo {insertadas}"

    personalizado = (
        "insert into clientes (nombre) values ('tres')\n"
        "--MI CORTE\n"
        "insert into clientes (nombre) values ('cuatro')"
    )
    ejecutar_sql(personalizado, engine, separador="--MI CORTE")
    insertadas = _contar(engine) - antes
    assert insertadas == 4, f"se esperaban 4 inserciones, hubo {insertadas}"
    log.info("OK separador por defecto y separador por llamada")


def _probar_atomicidad(engine) -> None:
    antes = _contar(engine)
    bloque = (
        "insert into clientes (nombre) values ('cinco')\n"
        f"{SEPARADOR_CONSULTAS}\n"
        "insert into clientes (nombre) values ('seis')\n"
        f"{SEPARADOR_CONSULTAS}\n"
        "insert into tabla_inexistente (x) values (1)"
    )
    try:
        ejecutar_sql(bloque, engine)
    except ExcepcionEjecucionSql as exc:
        assert exc.codigo_salida == 3, f"codigo de salida {exc.codigo_salida}"
        log.info("OK error SQL traducido a codigo 3")
    else:
        raise AssertionError("el bloque con una sentencia invalida no lanzo excepcion")

    despues = _contar(engine)
    assert despues == antes, f"la transaccion no se revirtio: {antes} filas antes, {despues} despues"
    log.info("OK atomicidad: %d filas antes y despues", antes)


def _probar_conexion_invalida() -> None:
    engine = create_engine("sqlite:///Z:/ruta/que/no/existe/base.db")
    try:
        ejecutar_sql("delete from clientes", engine)
    except ExcepcionConexion as exc:
        assert exc.codigo_salida == 2, f"codigo de salida {exc.codigo_salida}"
        log.info("OK conexion invalida traducida a codigo 2")
    else:
        raise AssertionError("una conexion invalida no lanzo ExcepcionConexion")


def _probar_entrada_invalida(engine) -> None:
    for descripcion, llamada in (
        ("sql vacio", lambda: ejecutar_sql("   ", engine)),
        ("separador vacio", lambda: ejecutar_sql("select 1", engine, separador=" ")),
        ("engine invalido", lambda: ejecutar_sql("select 1", "no es un engine")),  # ty: ignore[invalid-argument-type]
    ):
        try:
            llamada()
        except ValueError:
            continue
        raise AssertionError(f"{descripcion} deberia lanzar ValueError")
    log.info("OK entradas invalidas como ValueError nativo")


def _probar_sin_print_y_con_log(engine) -> None:
    salida = io.StringIO()
    capturado: list[str] = []

    class _Colector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capturado.append(record.getMessage())

    colector = _Colector()
    logger_ejecucion = logging.getLogger(ejecutar_sql.__module__)
    logger_ejecucion.addHandler(colector)
    logger_ejecucion.setLevel(logging.DEBUG)
    try:
        with redirect_stdout(salida):
            retorno = ejecutar_sql(
                "-- Encabezado auditable\ninsert into clientes (nombre) values ('siete')",
                engine,
            )
    finally:
        logger_ejecucion.removeHandler(colector)

    assert salida.getvalue() == "", f"la libreria imprimio en stdout: {salida.getvalue()!r}"
    assert retorno is None, f"ejecutar_sql debe devolver None, devolvio {retorno!r}"
    assert any("Encabezado auditable" in mensaje for mensaje in capturado), (
        f"el encabezado no se registro en el log: {capturado}"
    )
    assert any("filas afectadas" in mensaje for mensaje in capturado), (
        f"las filas afectadas no se registraron en el log: {capturado}"
    )
    log.info("OK retorno None, sin print, con encabezado y filas afectadas en el log")


def main() -> None:
    configurar_log()
    log.info("Test de ejecutar_sql")

    engine = _crear_engine()
    _probar_retorno_y_parametros(engine)
    _probar_backslash_intacto(engine)
    _probar_separador(engine)
    _probar_atomicidad(engine)
    _probar_conexion_invalida()
    _probar_entrada_invalida(engine)
    _probar_sin_print_y_con_log(engine)

    log.info("OK test_ejecutar_sql completo")


if __name__ == "__main__":
    main()
