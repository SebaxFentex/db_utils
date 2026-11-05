@echo off
cd /d "%~dp0.."
echo Construyendo paquete...
uv build
if errorlevel 1 (
    echo ERROR: la construccion fallo.
    pause
    exit /b 1
)
echo.
echo Artefactos generados en dist\:
dir /b dist
pause
