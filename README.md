# db_utils

Libreria interna para crear engines de SQLAlchemy y ejecutar bloques de SQL en
Oracle, SQL Server y Teradata.

```python
from db_utils import crear_engine_oracle, ejecutar_sql

engine = crear_engine_oracle(usuario="u", clave="c", host="servidor", servicio="SERVICIO")
ejecutar_sql("update tabla set estado = 1 where periodo = :periodo", engine, parametros={"periodo": "202609"})
```

## 1. Que hace y que no

**Hace**

- Construye engines de SQLAlchemy para Oracle (`oracle+oracledb`), SQL Server
  (`mssql+pymssql`) y Teradata (`teradatasql`) a partir de parametros explicitos.
- Ejecuta una o varias sentencias DDL/DML en **una sola transaccion**: si una
  falla, no queda ninguna aplicada. Devuelve `None`: el detalle queda en el log.
- Permite separar sentencias con un separador propio (`SEPARADOR_CONSULTAS` por
  defecto), asi un `.sql` con varias sentencias se ejecuta de una vez.
- Enlaza los valores como parametros ligados (`:nombre`): el valor queda
  aislado del texto del SQL.
- Traduce los errores de la base a dos excepciones propias con codigo de salida.

**No hace**

- No lee variables de entorno ni archivos `.env`: todo entra por parametro.
  El `.env` es del proyecto consumidor.
- No extrae a DataFrame ni reemplaza a `pandas.read_sql`. Si se necesita
  volumen, el consumidor usa pandas con el mismo engine.
- No reintenta, no programa corridas y no arma el correo de salida: eso es del
  proyecto que la usa.
- No inicializa Oracle Client por su cuenta: si el consumidor necesita modo
  thick, llama a `inicializar_cliente_oracle()` de forma explicita.
- No configura logging: solo emite. Si el consumidor no configura nada, no se
  imprime ni se escribe ningun archivo.

## 2. Como declararla en el proyecto consumidor

En el `pyproject.toml` de `python_<nombre>`, por Git con el tag fijo (nunca
`sys.path` ni copiar carpetas):

```toml
[project]
dependencies = ["db_utils"]

[tool.uv.sources]
db_utils = { git = "https://github.com/SebaxFentex/db_utils", tag = "v1.4.0" }
```

El repositorio es publico: no hacen falta credenciales. El `tag` fija la version
del codigo que se instala; para tomar otra hay que cambiarlo y resolver de nuevo.

```bash
uv lock && uv sync
```

## 3. Que necesita el proyecto consumidor

| Requisito | Detalle |
|---|---|
| Python | `>=3.14` |
| Gestor | `uv` (cada proyecto con su propio `.venv` y `uv.lock`) |
| Datos de conexion | Los define el proyecto en **su** `.env` (via su `env.py`) y los pasa como parametros |
| Login manual | No aplica: la libreria no pide credenciales ni MFA |
| Oracle Client | Solo si se necesita modo thick (`inicializar_cliente_oracle`), antes de la primera conexion |
| Driver SQL Server | `pymssql` viaja como dependencia de la libreria; no instalar aparte |
| Driver Teradata | `teradatasqlalchemy` viaja como dependencia de la libreria; no instalar aparte |

No hay `.bat` de la libreria que el consumidor deba ejecutar.

## 4. Ejemplo minimo

Una sentencia:

```python
from db_utils import crear_engine_sqlserver, ejecutar_sql

engine = crear_engine_sqlserver(
    usuario="usuario", clave="clave", host="servidor", base_datos="BASE",
)
ejecutar_sql(
    "update ventas set operador = :operador where periodo = :periodo",
    engine,
    parametros={"operador": "TIGO", "periodo": "202609"},
)
```

Varias sentencias en un bloque atomico:

```python
from db_utils import SEPARADOR_CONSULTAS, ejecutar_sql

sql = f"""
-- Limpia el periodo
delete from resumen where periodo = :periodo
{SEPARADOR_CONSULTAS}
-- Reinserta
insert into resumen (periodo, total) select :periodo, count(*) from ventas where periodo = :periodo
"""
ejecutar_sql(sql, engine, parametros={"periodo": "202609"})
```

Base SQL Server antigua que solo habla TDS 7.0:

```python
engine = crear_engine_sqlserver(
    usuario="usuario", clave="clave", host="servidor", base_datos="BASE",
    query={"tds_version": "7.0"},
)
```

Teradata:

```python
from db_utils import crear_engine_teradata

engine = crear_engine_teradata(
    usuario="usuario", clave="clave", host="servidor", base_datos="BASE",
)
```

## 5. API publica

### `crear_engine_oracle(usuario, clave, host, servicio, puerto=1521, query=None) -> Engine`

Construye el engine de Oracle. `query` agrega opciones a la URL.
**Lanza** `TypeError` si un parametro no es texto y `ValueError` si llega vacio o
el puerto no es valido. La conexion se abre en el primer uso.

### `crear_engine_sqlserver(usuario, clave, host, base_datos, puerto=None, query=None) -> Engine`

Construye el engine de SQL Server con `pymssql`. `puerto=None` usa el default del
driver (1433). `query` es el lugar para `{"tds_version": "7.0"}` en bases
antiguas. **Lanza** `TypeError` o `ValueError` con las mismas reglas que Oracle.

### `crear_engine_teradata(usuario, clave, host, base_datos) -> Engine`

Construye el engine de Teradata con el dialecto `teradatasql`.
**Lanza** `TypeError` si un parametro no es texto y `ValueError` si llega vacio.
La conexion se abre en el primer uso.

### `inicializar_cliente_oracle(ruta_cliente) -> None`

Inicializa Oracle Client (modo thick). Sin esta llamada oracledb trabaja en modo
thin, que es el default. **Debe llamarse antes de abrir cualquier conexion**: si
el proceso ya creo una conexion en modo thin, oracledb rechaza el cambio y queda
en thin. Es idempotente: repetir con la misma ruta no tiene efecto y con otra
ruta falla.
**Lanza** `TypeError` si la ruta no es texto, `ValueError` si llega vacia y
`ExcepcionConexion` (codigo 2) si no contiene un cliente utilizable.

### `ejecutar_sql(sql, engine, parametros=None, separador=SEPARADOR_CONSULTAS) -> None`

Ejecuta el bloque en una transaccion. **No devuelve filas**: el encabezado `--`
de cada sentencia y las filas afectadas quedan en el log.

- `parametros`: dict para los marcadores `:nombre`. Un parametro que no aparece
  en la sentencia se ignora; si falta uno que la sentencia usa, la base responde
  con error y se traduce a `ExcepcionEjecucionSql`.
- `separador`: texto que corta el bloque. Cambiarlo solo afecta a esa llamada
  (no hay estado global).
- **Lanza** `ValueError` si el SQL o el separador estan vacios o si `engine` no es
  un `Engine` de SQLAlchemy, `ExcepcionConexion` (codigo 2) si no se pudo conectar,
  `ExcepcionEjecucionSql` (codigo 3) si la base rechazo una sentencia. La
  transaccion completa queda revertida, sin sentencias a medias.

### `SEPARADOR_CONSULTAS`

Constante con el separador por defecto: `"--SEPARADOR DE CONSULTAS"`.

## 6. Codigos de salida

| Codigo | Significado | Cuando se usa |
|---|---|---|
| `0` | correcto | la ejecucion termino sin errores |
| `1` | fallo generico | convencion Python (`ExcepcionDb` base, errores no clasificados) |
| `2` | conexion | no se pudo conectar, se perdio la conexion o fallo el Oracle Client |
| `3` | SQL | la base rechazo una sentencia; la transaccion quedo revertida |

Los codigos propios (2 en adelante) son de esta libreria y no se comparten con
otras. El consumidor propaga sin repetir el numero:

```python
import sys
from db_utils import ExcepcionDb

try:
    ejecutar_sql(sql, engine)
except ExcepcionDb as exc:
    log.error("Fallo la ejecucion: %s", exc)
    sys.exit(exc.codigo_salida)
```

## 7. Desarrollo

```bash
uv sync                 # crea .venv con las dependencias del lock
uv run python tests/test_ejecutar_sql.py
uv run python tests/test_crear_engines.py
uv run --env-file .env python tests/test_conexion.py   # e2e, requiere .env
```

Los dos primeros no necesitan credenciales (sqlite en memoria). El e2e usa los
datos de `.env` (copiar `.env.example`) y falla con mensaje si no estan.

```text
src/db_utils/
  __init__.py        NullHandler + API publica
  _excepciones.py    ExcepcionDb, ExcepcionConexion, ExcepcionEjecucionSql
  conexion.py        crear_engine_oracle / crear_engine_sqlserver / crear_engine_teradata / inicializar_cliente_oracle
  ejecucion.py       SEPARADOR_CONSULTAS, ejecutar_sql
Ejecutables/         build.bat, abrir_vscode.bat y tests/ (un .bat por test)
tests/               los tres tests; el unico lugar del ecosistema con tests
logs/                logs de desarrollo del test (ignorado por git)
```

El detalle de arquitectura, reglas inviolables e historial de rupturas esta en
`AGENTS.md`.
