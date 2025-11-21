@echo off
REM Eva Development Startup Script (Batch fallback)
REM For systems where PowerShell is unavailable

echo.
echo ================================================
echo     Eva - Character Companion (Dev Mode)
echo ================================================
echo.

REM Get project root (parent of scripts directory)
cd /d "%~dp0.."
set PROJECT_ROOT=%CD%

REM Check Docker
echo Checking prerequisites...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker not found. Please install Docker Desktop.
    exit /b 1
)

docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker daemon not running. Please start Docker Desktop.
    exit /b 1
)
echo [OK] Docker is running

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    exit /b 1
)
echo [OK] Python found

REM Check virtual environment
if not exist "%PROJECT_ROOT%\server\venv" (
    echo ERROR: Virtual environment not found
    echo Run: cd server ^&^& python -m venv venv ^&^& pip install -r requirements.txt
    exit /b 1
)
echo [OK] Virtual environment exists

echo.

REM Start Docker services
echo Starting Docker services...
cd "%PROJECT_ROOT%\docker"

REM Check if containers are running by counting output lines from ps --quiet
for /f %%i in ('docker-compose ps --quiet 2^>nul ^| find /c /v ""') do set CONTAINER_COUNT=%%i
if "%CONTAINER_COUNT%"=="0" (
    docker-compose up -d
    if errorlevel 1 (
        echo ERROR: Failed to start Docker services
        exit /b 1
    )
    echo [OK] Docker services started
) else (
    echo [OK] Docker containers already running
)

cd "%PROJECT_ROOT%"
echo.

REM Wait for services (simplified - just wait 10 seconds)
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul
echo [OK] Services should be ready

echo.

REM Simple database check (just try to start, let Python handle errors)
echo Starting Eva terminal interface...
echo.
echo ================================================
echo.

cd "%PROJECT_ROOT%\server"

REM Activate venv and run terminal with restart loop
call venv\Scripts\activate.bat

:restart_loop
python -m app.terminal.main
set EXIT_CODE=%ERRORLEVEL%

if "%EXIT_CODE%"=="99" (
    echo.
    echo Restarting in 5 seconds...
    timeout /t 5 /nobreak >nul
    echo.
    echo ================================================
    echo.
    goto restart_loop
)

echo.
echo ================================================
echo.

REM Ask about stopping Docker
set /p STOP_DOCKER="Stop Docker containers? [y/N]: "
if /i "%STOP_DOCKER%"=="y" (
    echo Stopping Docker services...
    cd "%PROJECT_ROOT%\docker"
    docker-compose down
    echo [OK] Docker services stopped
) else (
    echo Docker services left running
)

echo.
echo Goodbye!
echo.
