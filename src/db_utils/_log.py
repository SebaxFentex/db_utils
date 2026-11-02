"""Configuracion de log para los entrypoints (tests, ejecutables).

La libreria emite logs via logging.getLogger(__name__); este modulo configura el
logger "db_utils" cuando el entrypoint lo llama.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

PREFIJO_LOG_PREDETERMINADO = "db-"
NIVEL_LOG_PREDETERMINADO = "INFO"
MAX_LOGS_PREDETERMINADO = 30


def carpeta_logs() -> Path:
    """Carpeta logs/ en la raiz del proyecto (solo desarrollo: tests)."""
    return Path(__file__).resolve().parents[2] / "logs"


def purgar_logs(
    carpeta: Path,
    conservar: int = MAX_LOGS_PREDETERMINADO,
    prefijo: str = PREFIJO_LOG_PREDETERMINADO,
) -> None:
    """Borra los .log mas viejos dejando los `conservar` recientes (por nombre)."""
    archivos = sorted(carpeta.glob(f"{prefijo}*.log"))
    for viejo in archivos[: max(0, len(archivos) - conservar)]:
        viejo.unlink(missing_ok=True)


def configurar_log(
    nivel: str | None = None,
    prefijo: str = PREFIJO_LOG_PREDETERMINADO,
    conservar: int = MAX_LOGS_PREDETERMINADO,
) -> logging.Logger:
    """Configura archivo + consola para el logger "db_utils". Idempotente.

    Nivel: parametro > env DB_NIVEL_LOG > NIVEL_LOG_PREDETERMINADO.
    Valor invalido cae a NIVEL_LOG_PREDETERMINADO. Prefijo y retencion llegan
    por parametro (defaults "db-" y 30).
    El NullHandler que la libreria agrega en db_utils/__init__.py no cuenta
    como configuracion: se ignora a proposito para poder configurarlo aqui.
    """
    resuelto = (nivel or os.environ.get("DB_NIVEL_LOG", NIVEL_LOG_PREDETERMINADO)).upper()
    if resuelto not in logging.getLevelNamesMapping():
        resuelto = NIVEL_LOG_PREDETERMINADO

    logger = logging.getLogger("db_utils")
    if any(not isinstance(h, logging.NullHandler) for h in logger.handlers):
        return logger

    carpeta = carpeta_logs()
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo_log = carpeta / f"{prefijo}{datetime.now():%Y%m%d-%H%M%S}.log"

    manejador_archivo = logging.FileHandler(archivo_log, encoding="utf-8")
    manejador_consola = logging.StreamHandler()
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    manejador_archivo.setFormatter(formato)
    manejador_consola.setFormatter(formato)
    logger.addHandler(manejador_archivo)
    logger.addHandler(manejador_consola)
    logger.setLevel(resuelto)

    purgar_logs(carpeta, conservar=conservar, prefijo=prefijo)
    logger.info("Log en: %s (nivel %s)", archivo_log, resuelto)
    return logger
