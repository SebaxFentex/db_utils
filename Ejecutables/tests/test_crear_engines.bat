@echo off
cd /d "%~dp0..\.."
uv run python tests/test_crear_engines.py
set EXIT_CODE=%ERRORLEVEL%
echo.
echo Codigo de salida: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
