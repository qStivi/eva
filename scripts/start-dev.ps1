# Eva Development Startup Script
# Starts Docker services, waits for health checks, initializes DB, and launches terminal

param(
    [switch]$Debug,
    [switch]$SkipDocker,
    [switch]$SkipDbInit
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Banner
Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host "    Eva - Character Companion (Dev Mode)        " -ForegroundColor Magenta
Write-Host "================================================" -ForegroundColor Magenta
Write-Host ""

# Get project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check Docker
if (-not $SkipDocker) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "ERROR: Docker not found. Please install Docker Desktop."
        exit 1
    }

    # Check if Docker is running
    try {
        docker ps | Out-Null
    } catch {
        Write-Error "ERROR: Docker daemon not running. Please start Docker Desktop."
        exit 1
    }
    Write-Success "OK Docker is running"
}

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: Python not found. Please install Python 3.10+"
    exit 1
}
Write-Success "OK Python found"

# Check virtual environment
$VenvPath = Join-Path $ProjectRoot "server\venv"
if (-not (Test-Path $VenvPath)) {
    Write-Error "ERROR: Virtual environment not found at $VenvPath"
    Write-Info "Run: cd server && python -m venv venv && pip install -r requirements.txt"
    exit 1
}
Write-Success "OK Virtual environment exists"

# Check .env file
$EnvFile = Join-Path $ProjectRoot "server\.env"
if (-not (Test-Path $EnvFile)) {
    Write-Warning "WARNING: .env file not found. Using defaults."
    Write-Info "Consider copying server\.env.example to server\.env"
}

Write-Host ""

# Start Docker services
if (-not $SkipDocker) {
    Write-Info "Starting Docker services..."
    Set-Location (Join-Path $ProjectRoot "docker")

    # Check if containers are already running
    # Use --quiet to get container IDs (more reliable than --filter which is ignored)
    $RunningContainerIds = @(docker-compose ps --quiet 2>$null)
    if ($RunningContainerIds.Count -gt 0) {
        Write-Success "OK Docker containers already running (skipping start)"
    } else {
        docker-compose up -d
        if ($LASTEXITCODE -ne 0) {
            Write-Error "ERROR: Failed to start Docker services"
            exit 1
        }
        Write-Success "OK Docker services started"
    }

    Set-Location $ProjectRoot
    Write-Host ""

    # Wait for services to be healthy
    Write-Info "Waiting for services to be ready..."
    & "$PSScriptRoot\wait-for-services.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ERROR: Services failed to become healthy"
        exit 1
    }
    Write-Host ""
}

# Initialize database if needed
if (-not $SkipDbInit) {
    Write-Info "Checking database..."
    & "$PSScriptRoot\init-database.ps1" -CheckOnly

    if ($LASTEXITCODE -eq 2) {
        # Database not initialized
        Write-Warning "Database not initialized."
        $Response = Read-Host "Create database tables? [Y/n]"

        if ($Response -eq "" -or $Response -eq "y" -or $Response -eq "Y") {
            & "$PSScriptRoot\init-database.ps1"
            if ($LASTEXITCODE -ne 0) {
                Write-Error "ERROR: Database initialization failed"
                exit 1
            }
        } else {
            Write-Error "ERROR: Cannot start without database. Exiting."
            exit 1
        }
    } elseif ($LASTEXITCODE -eq 0) {
        Write-Success "OK Database already initialized"
    } else {
        Write-Error "ERROR: Database check failed"
        exit 1
    }
    Write-Host ""
}

# Launch terminal interface
Write-Info "Starting Eva terminal interface..."
Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host ""

Set-Location (Join-Path $ProjectRoot "server")

# Activate virtual environment and run terminal
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

# Build command arguments
$TerminalArgs = @("-m", "app.terminal.main")
if ($Debug) {
    $TerminalArgs += "--debug"
}

# Run in loop to support /restart command
$RestartLoop = $true
while ($RestartLoop) {
    # Activate venv and run terminal
    & $ActivateScript
    $Process = Start-Process -FilePath "python" -ArgumentList $TerminalArgs -Wait -PassThru -NoNewWindow

    $ExitCode = $Process.ExitCode

    if ($ExitCode -eq 99) {
        # Restart requested
        Write-Host ""
        Write-Info "Restarting in 5 seconds..."
        Start-Sleep -Seconds 5
        Write-Host ""
        Write-Host "================================================" -ForegroundColor Magenta
        Write-Host ""
        continue
    } else {
        # Normal exit or error
        $RestartLoop = $false
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host ""

# Ask about stopping Docker
if (-not $SkipDocker) {
    $Response = Read-Host "Stop Docker containers? [y/N]"

    if ($Response -eq "y" -or $Response -eq "Y") {
        Write-Info "Stopping Docker services..."
        Set-Location (Join-Path $ProjectRoot "docker")
        docker-compose down
        Set-Location $ProjectRoot
        Write-Success "OK Docker services stopped"
    } else {
        Write-Info "Docker services left running (fast restart next time)"
    }
}

# Return to original directory
Set-Location $ProjectRoot

Write-Host ""
Write-Success "Goodbye!"
Write-Host ""
