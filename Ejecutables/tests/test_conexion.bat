@echo off
cd /d "%~dp0..\.."
if exist ".env" (
    uv run --env-file .env python tests/test_conexion.py
) else (
    echo Aviso: no hay .env local; copie .env.example y complete los datos.
    uv run python tests/test_conexion.py
)
set EXIT_CODE=%ERRORLEVEL%
echo.
echo Codigo de salida: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
