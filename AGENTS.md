# AGENTS.md — db_utils

Guia para agentes (y humanos) que trabajan en este repo. Cada regla con su
"porque" viene de un defecto real; no relajarla sin evidencia nueva.

## 1. Proyecto en 30 segundos

Libreria interna PAQUETE (`uv_build`, layout `src/`) que construye engines de
SQLAlchemy para Oracle, SQL Server y Teradata y ejecuta bloques de SQL en una sola
transaccion. Se publica en `https://github.com/SebaxFentex/db_utils` y los
proyectos de `D:\Tigo\Proyectos` la declaran por Git con un tag fijo en su
`[tool.uv.sources]`; no se opera con el Programador de tareas y no pide
credenciales a ningun humano.

Stack: Python 3.14, `uv`, SQLAlchemy 2.1, `oracledb` 26 (thin por defecto),
`pymssql` 2.4, `teradatasqlalchemy` 20 (dialecto `teradatasql`).

```text
src/db_utils/
  __init__.py        NullHandler + API publica (sin re-exports de modulos internos)
  _excepciones.py    ExcepcionDb (1), ExcepcionConexion (2), ExcepcionEjecucionSql (3)
  conexion.py        crear_engine_oracle / crear_engine_sqlserver / crear_engine_teradata / inicializar_cliente_oracle
  ejecucion.py       SEPARADOR_CONSULTAS, ejecutar_sql
Ejecutables/
  build.bat          uv build y lista dist/
  abrir_vscode.bat   abre la raiz de la libreria
  tests/             un .bat por test (mismo nombre que el .py)
tests/
  test_ejecutar_sql.py   local, sqlite en memoria (sin credenciales)
  test_crear_engines.py  local, inspecciona la URL del engine (sin conectar)
  test_conexion.py       e2e contra Oracle/SQL Server/Teradata, lee .env
logs/                    logs de desarrollo (ignorado por git)
```

## 2. Arquitectura y API

- **La libreria no lee entorno.** `import db_utils` no exige ninguna variable y
  no abre conexiones. Todo entra por parametro: el `.env` es del consumidor.
- `crear_engine_oracle(usuario, clave, host, servicio, puerto=1521, query=None)`,
  `crear_engine_sqlserver(usuario, clave, host, base_datos, puerto=None, query=None)`
  y `crear_engine_teradata(usuario, clave, host, base_datos)`:
  construyen la URL y devuelven un `Engine` con `pool_pre_ping=True` y
  `pool_recycle=1800`. No conectan.
- `query` es la valvula para opciones del driver. **Las bases antiguas que solo
  hablan TDS 7.0 se conectan pasando `query={"tds_version": "7.0"}` desde el
  proyecto consumidor**.
- `ejecutar_sql(sql, engine, parametros=None, separador=SEPARADOR_CONSULTAS)`
  ejecuta bloques DDL/DML y **devuelve `None`**: el encabezado de cada sentencia
  y las filas afectadas van al log. Abre la conexion fuera de la transaccion para
  poder distinguir el error de conexion (2) del error de SQL (3).
- `inicializar_cliente_oracle(ruta_cliente)` es el unico punto que toca estado
  del proceso (modo thick) y solo se llama si el consumidor lo pide. La
  idempotencia la da `oracledb`: repetir con los mismos argumentos no hace nada
  y con argumentos distintos falla, asi que el paquete no guarda estado propio.
  Debe invocarse **antes** de abrir cualquier conexion: si el proceso ya creo
  una conexion en modo thin, `oracledb` rechaza el cambio y sigue en thin.
- Orden de metodos y funciones: publicas primero, privadas (`_nombre`) despues.

## 3. Reglas inviolables

1. **Cero lecturas de entorno en la libreria.** Ningun modulo de `src/`
   importa `os`: los tests leen `DB_NIVEL_LOG` y lo pasan como parametro a
   `log_utils.configurar_log`. Un valor que cambia por maquina se pasa
   como parametro.
2. **Parametros ligados, nunca interpolacion.** Los valores viajan por
   `:nombre` a SQLAlchemy. Interpolar con `re.sub` corrompe datos (un `\n` de
   una ruta Windows se convierte en salto de linea) y abre inyeccion de SQL.
   Prohibido volver a construir SQL con f-strings o `%`.
3. **Una transaccion por llamada.** Nada de `commit()` por sentencia: un bloque
   de cinco updates dejaba dos aplicados si el tercero fallaba.
4. **La libreria emite, el entrypoint configura.** `logging.getLogger(__name__)`
   en cada modulo y `NullHandler` en el paquete; `configurar_log()` solo se llama
   desde `tests/*` via `log_utils.configurar_log()`. Prohibido `basicConfig()` y
   prohibido que un modulo que emite agregue manejadores: el unico que agrega es
   `log_utils`, y lo hace sobre el logger "db_utils", nunca sobre el raiz del consumidor.
5. **Sin `print()`.** El unico destino de las trazas es `log`; un proceso
   desatendido con `print` no deja rastro. El encabezado `--` de cada sentencia
   se registra en INFO (rastro auditable) y el detalle en DEBUG.
6. **Nada de objetos globales mutables.** El separador es un parametro con
   default; `set_separador()` y el `SEPARADOR` re-exportado se eliminaron porque
   el `__init__` se quedaba con la copia hecha al importar y mentia. El estado de
   proceso del modo thick tampoco vive aca: lo administra `oracledb` (ver
   `inicializar_cliente_oracle`), asi que el paquete no tiene ninguna variable
   global.
7. **Sin efectos al importar.** Prohibido crear engines a nivel de modulo y
   tragarte la excepcion con `except Exception: engine = None`: el consumidor
   descubria el problema mucho despues.
8. **Errores clasificados por donde ocurren.** Conexion (2) es lo que falla al
   abrir o al perder la conexion, incluido el `OSError`/`socket.gaierror` que
   `oracledb` thin lanza antes de que SQLAlchemy lo envuelva. SQL (3) es lo que
   rechaza la base. La entrada malformada se deja nativa: `TypeError` si el
   valor no es texto (`None`, un numero) y `ValueError` si es texto pero llega
   vacio o solo con espacios. Nunca se envuelve en `ExcepcionDb`.
9. **`.bat` de proceso en `Ejecutables/` invocando `uv run`.** Un `.bat` por
   test en `Ejecutables/tests/`, con `pause` para leer el resultado y
   propagacion del codigo de salida. `abrir_vscode.bat` es utilitario: no lleva
   `uv run`.
10. **Nada especulativo.** Sin abstracciones de un solo uso ni parametros de
    "por si acaso". Lo muerto se borra: queda en git si se necesita.
11. **La descripcion del docstring dice que hace la funcion, nada mas.** Los
    primeros parrafos (antes de `Args`/`Raises`/`Notes`) describen la funcion
    misma; lo que hace la dependencia (`oracledb` en thin por defecto, `pymssql`
    y su version de TDS) va en `Notes` o en el README. `Args`, `Returns` y
    `Raises` si pueden explicar el porque de un parametro, un error o un valor
    devuelto. La descripcion no compara con otras librerias ni con versiones
    anteriores: el contrato se enuncia en positivo ("devuelve `None`", no "no
    devuelve filas"). Las fronteras de alcance (que no lee `.env`, que no migra,
    que no manda correo) van una sola vez, en la seccion 1 del README.

## 4. Logging, codigos de salida y `.env`

- Los tests llaman `log_utils.configurar_log(nombre="db_utils",
  carpeta_logs=<repo>/logs, nivel_archivo/nivel_consola=os.environ.get("DB_NIVEL_LOG"),
  prefijo="db_utils-")`: archivo en DEBUG y consola en INFO, cada uno con su
  formato, purga los antiguos e idempotente. Sin `DB_NIVEL_LOG` rigen los
  defaults de `log_utils`. Devuelve el `Logger` configurado.
- Codigos: `0` correcto · `1` fallo generico · `2` conexion · `3` SQL. El
  consumidor hace `sys.exit(exc.codigo_salida)`.
- `.env` local (ignorado por git) solo lo usa `tests/test_conexion.py`. Se
  versiona `.env.example` con placeholders: `ORACLE_USUARIO`, `ORACLE_CLAVE`,
  `ORACLE_HOST`, `ORACLE_SERVICIO` (y opcionales `ORACLE_PUERTO`,
  `ORACLE_RUTA_CLIENTE`), `SQLSERVER_USUARIO`, `SQLSERVER_CLAVE`,
  `SQLSERVER_HOST`, `SQLSERVER_BD` (y opcionales `SQLSERVER_PUERTO`,
  `SQLSERVER_TDS`), `TERADATA_USUARIO`, `TERADATA_CLAVE`, `TERADATA_HOST`,
  `TERADATA_BD`, `DB_NIVEL_LOG`.
- Nunca loguear credenciales: para describir un engine se usa
  `engine.url.render_as_string(hide_password=True)`.

## 5. Verificacion antes de dar por hecho

1. `uv run python -m compileall -q src/db_utils`.
2. `import db_utils` con el entorno vacio: sin error, `handlers` con el
   `NullHandler` y ningun engine creado.
3. `uv run python tests/test_ejecutar_sql.py` y `uv run python tests/test_crear_engines.py`
   en 0. El e2e (`tests/test_conexion.py`) necesita credenciales reales: si no
   hay `.env`, se reporta como no verificado en vez de darlo por bueno.
4. `uv build` sin advertencias de `build_system.requires`; el wheel debe traer
   `db_utils/__init__.py`.
5. Greps de guardia: cero `getenv`/`os.environ` en `src/`, cero
   `print(`, cero `basicConfig`, cero `set_separador`, cero `_from_env`, cero
   `load_dotenv`, cero `cwd(`.
6. Los `.bat` se prueban ejecutandolos: `cmd.exe /c Ejecutables\build.bat` debe
   llegar al `pause` final listando `dist\`.

## 6. Historial

- **0.2.0** — Primera version del paquete `uv_build` con layout `src/`: API por
  parametros (`crear_engine_oracle`, `crear_engine_sqlserver`, `ejecutar_sql`),
  sin lecturas de entorno y sin engines globales.
- **0.2.1** — `_log.py` alineado con el de `sharepoint`; dependencias al dia.
- **0.2.2** — Helpers internos renombrados para que el nombre diga que hacen.
- **0.3.0** — La validacion de parametros separa `TypeError` (tipo incorrecto) de
  `ValueError` (contenido vacio).
- **0.4.0** — `ejecutar_sql` devuelve `None` y las filas afectadas van al log; se
  elimina la clase `ResultadoSql`.
- **1.0.0** — Primera version estable: el contrato se enuncia en positivo, las
  fronteras de alcance quedan solo en el README y la instalacion en los
  consumidores pasa a ser por Git con tag fijo, no editable.
- **1.1.0** — La libreria pasa a llamarse `db_utils` (repositorio
  `SebaxFentex/db_utils`): cambian la carpeta, el paquete (`src/db_utils`), el
  nombre de la distribucion y el logger. El prefijo de los archivos de log
  (`db-`) y la variable `DB_NIVEL_LOG` no cambian: renombrar la libreria no
  arrastra la configuracion de quien la consume. Rompe el import de cualquier
  consumidor que todavia haga `import db`.
- **1.3.0** — Logging via `log_utils` (v0.1.0, dependencia por Git con tag):
  se elimina `src/db_utils/_log.py`; los tests llaman
  `log_utils.configurar_log` con archivo en DEBUG y consola en INFO.
- **1.2.0** — El prefijo de log pasa a `db_utils-` (igual que el logger y el
  paquete); los tests traducen a `SystemExit(exc.codigo_salida)`; imports
  absolutos en el paquete; `LICENSE` MIT y `.gitattributes` (LF) en la raiz.
