@echo off
title Instalar dependencias IIS - Estudio (mismo patron que Rutas)
color 0E

REM IIS usa C:\Python\python.exe (ver web.config processPath).
REM Ejecutar en el servidor, en la carpeta del sitio (ej. C:\inetpub\wwwroot\Estudio).

set "PY_IIS=C:\Python\python.exe"
set "SITE_DIR=%~dp0"
if "%SITE_DIR:~-1%"=="\" set "SITE_DIR=%SITE_DIR:~0,-1%"

echo ========================================
echo    Instalacion IIS - Estudio
echo    Python: %PY_IIS%
echo    Carpeta: %SITE_DIR%
echo ========================================
echo.

if not exist "%PY_IIS%" (
    echo ERROR: No existe %PY_IIS%
    echo Edita PY_IIS en este .bat para que coincida con processPath en web.config
    pause
    exit /b 1
)

if not exist "%SITE_DIR%\requirements.txt" (
    echo ERROR: No se encontro requirements.txt en %SITE_DIR%
    pause
    exit /b 1
)

if not exist "%SITE_DIR%\logs" mkdir "%SITE_DIR%\logs"

echo [1/4] Instalando dependencias en el Python de IIS...
"%PY_IIS%" -m pip install -r "%SITE_DIR%\requirements.txt"
if errorlevel 1 (
    echo ERROR: Fallo la instalacion de dependencias
    pause
    exit /b 1
)

echo.
echo [2/4] Comprobando modulos...
"%PY_IIS%" -c "import flask, flask_login, sqlalchemy, pyodbc, waitress; print('OK modulos principales')"
if errorlevel 1 (
    echo ERROR: Faltan modulos en %PY_IIS%
    pause
    exit /b 1
)

echo.
echo [3/4] Comprobando arranque de la app...
"%PY_IIS%" -c "import os, sys; sys.path.insert(0, r'%SITE_DIR%'); os.chdir(r'%SITE_DIR%'); from run import app; print('OK create_app')"
if errorlevel 1 (
    echo ERROR: La app no arranca. Revisa .env y conexion SQL.
    pause
    exit /b 1
)

echo.
echo [4/4] Actualizando web.config con la ruta del sitio...
> "%SITE_DIR%\web.config" (
echo ^<?xml version="1.0" encoding="utf-8"?^>
echo ^<configuration^>
echo   ^<system.webServer^>
echo.
echo     ^<handlers^>
echo       ^<add name="httpPlatformHandler"
echo            path="*"
echo            verb="*"
echo            modules="httpPlatformHandler"
echo            resourceType="Unspecified" /^>
echo     ^</handlers^>
echo.
echo     ^<httpPlatform
echo         processPath="C:\Python\python.exe"
echo         arguments="wsgi.py"
echo         stdoutLogEnabled="true"
echo         stdoutLogFile="%SITE_DIR%\logs\stdout.log"^>
echo.
echo       ^<environmentVariables^>
echo         ^<environmentVariable name="HTTP_PLATFORM_PORT" value="%%HTTP_PLATFORM_PORT%%" /^>
echo       ^</environmentVariables^>
echo.
echo     ^</httpPlatform^>
echo.
echo   ^</system.webServer^>
echo ^</configuration^>
)

echo web.config generado: %SITE_DIR%\web.config
echo.
echo Listo. Reinicia el sitio Estudio en IIS.
echo Prueba: https://estudio.malla.es/login
echo Logs: %SITE_DIR%\logs\stdout.log y %SITE_DIR%\logs\wsgi.log
echo.
pause
