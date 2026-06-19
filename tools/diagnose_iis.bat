@echo off
setlocal
cd /d "%~dp0\.."

echo === Diagnostico Estudio IIS (patron Rutas) ===
echo Carpeta: %cd%
echo.

set "PY_IIS=C:\Python\python.exe"
if not exist "%PY_IIS%" (
    echo [ERROR] No existe %PY_IIS%. Debe coincidir con processPath en web.config
    exit /b 1
)
echo [OK] Python IIS: %PY_IIS%
"%PY_IIS%" --version
echo.

if not exist ".env" (
    echo [AVISO] No hay .env
) else (
    echo [OK] .env presente
)

if not exist "sql\estudio_schema.sql" (
    echo [ERROR] Falta sql\estudio_schema.sql
) else (
    echo [OK] sql\estudio_schema.sql
)

if not exist "web.config" (
    echo [ERROR] Falta web.config
) else (
    echo [OK] web.config
    findstr /C:"processPath" web.config
    findstr /C:"stdoutLogFile" web.config
)

echo.
echo Configuracion BD Presencia (login):
"%PY_IIS%" -c "import os, sys; sys.path.insert(0, r'%cd%'); os.chdir(r'%cd%'); from app.config import settings; print('  servidor:', settings.presencia_db_server); print('  base:', settings.presencia_db_name); print('  usuario:', settings.presencia_db_user or '(vacio)'); print('  trusted:', settings.presencia_db_trusted_connection)"

echo.
echo Probando conexion BD Presencia...
"%PY_IIS%" -c "import os, sys; sys.path.insert(0, r'%cd%'); os.chdir(r'%cd%'); from sqlalchemy import text; from app.presencia.database import PresenciaSessionLocal; db=PresenciaSessionLocal(); db.execute(text('SELECT 1')); db.close(); print('[OK] Conexion Presencia')"
if errorlevel 1 (
    echo [ERROR] No conecta a Presencia. Revisa PRESENCIA_DB_* o PRESENCIA_ENV_FILE en .env
)

echo.
"%PY_IIS%" -c "import os, sys; sys.path.insert(0, r'%cd%'); os.chdir(r'%cd%'); from run import app; print('[OK] run.app')"
if errorlevel 1 (
    echo [ERROR] La app no importa. Ejecuta: install_iis.bat
    exit /b 1
)

echo.
echo Ultimas lineas de logs\wsgi.log:
if exist "logs\wsgi.log" (
    powershell -NoProfile -Command "Get-Content 'logs\wsgi.log' -Tail 25"
) else (
    echo (sin wsgi.log)
)

echo.
echo Ultimas lineas de logs\stdout.log:
if exist "logs\stdout.log" (
    powershell -NoProfile -Command "Get-Content 'logs\stdout.log' -Tail 25"
) else (
    echo (sin stdout.log)
)

echo.
echo 1. Recicla App Pool en IIS
echo 2. Prueba https://estudio.malla.es/
echo 3. Si falla login, revisa PRESENCIA_DB_* en .env (nombre correcto: ControlPresencia)
echo.
exit /b 0
