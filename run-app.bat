@echo off
REM ============================================================
REM TEAF Reference App - Entorno + Aplicación en Windows
REM ============================================================
REM Uso: guarda como run-app.bat en la raíz de teaf-reference-app
REM      y ejecuta: run-app.bat

setlocal enabledelayedexpansion

REM Verifica si estamos en el directorio correcto
if not exist "pyproject.toml" (
    echo ERROR: ejecuta este script desde la raiz de teaf-reference-app
    exit /b 1
)

echo.
echo ============================================================
echo TEAF Reference App - Reconstruccion + Ejecucion
echo ============================================================
echo.

REM ============================================================
REM PASO 1: PREPARAR ENTORNO
REM ============================================================

echo [1/7] Desactivando venv anterior...
call deactivate 2>nul

echo [2/7] Borrando .venv antiguo...
if exist ".venv" (
    rmdir /s /q .venv
    if errorlevel 1 (
        echo ERROR al borrar .venv
        pause
        exit /b 1
    )
)

echo [3/7] Verificando framework en ../torus-enterprise-framework...
if not exist "..\torus-enterprise-framework\teaf\__init__.py" (
    echo ERROR: no encuentro ../torus-enterprise-framework/teaf/__init__.py
    echo Asegurate de que la carpeta del framework este en: %CD%\..\torus-enterprise-framework
    pause
    exit /b 1
)

echo [4/7] Creando venv con Python 3.14...
py -3.14 -m venv .venv >nul 2>&1
if errorlevel 1 (
    echo ADVERTENCIA: Python 3.14 no encontrado
    echo Intentando con Python 3.13...
    py -3.13 -m venv .venv
    if errorlevel 1 (
        echo ERROR: no se pudo crear venv
        echo Instala Python 3.13 o 3.14 desde https://www.python.org
        pause
        exit /b 1
    )
)

echo [5/7] Activando venv...
call .venv\Scripts\activate.bat

echo [6/7] Actualizando pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel -q
if errorlevel 1 (
    echo ERROR en pip upgrade
    pause
    exit /b 1
)

echo [7/7a] Instalando TEAF desde ../torus-enterprise-framework...
python -m pip install -e ..\torus-enterprise-framework >nul 2>&1
if errorlevel 1 (
    echo ERROR: falló instalar TEAF
    echo Intenta manualmente:
    echo   cd teaf-reference-app
    echo   .venv\Scripts\activate.bat
    echo   python -m pip install -e ../torus-enterprise-framework
    pause
    exit /b 1
)

echo [7/7b] Instalando teaf-reference-app + dev...
python -m pip install -e ".[dev]" >nul 2>&1
if errorlevel 1 (
    echo ERROR: falló instalar reference app
    pause
    exit /b 1
)

echo.
echo ============================================================
echo OK - Entorno listo
echo ============================================================
echo.

REM ============================================================
REM PASO 2: VERIFICAR INSTALACION
REM ============================================================

echo Verificando TEAF...
python -c "import teaf; print('✓ TEAF', teaf.__version__)" 2>nul
if errorlevel 1 (
    echo ERROR: no se puede importar teaf
    pause
    exit /b 1
)

python -c "from teaf import Application; print('✓ Application importable')" 2>nul
if errorlevel 1 (
    echo ERROR: no se puede importar Application
    pause
    exit /b 1
)

REM ============================================================
REM PASO 3: EJECUTAR APLICACION
REM ============================================================

echo.
echo ============================================================
echo Iniciando aplicacion en http://127.0.0.1:8000
echo ============================================================
echo.
echo Presiona CTRL+C para detener el servidor
echo.

REM Abre el navegador (espera 3 segundos a que arrange el servidor)
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000

REM Ejecuta uvicorn en foreground (el usuario ve logs)
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

REM Si llegamos aqui, el usuario presiono CTRL+C
echo.
echo Aplicacion detenida.
pause
