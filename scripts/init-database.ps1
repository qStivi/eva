# Database initialization script
# Creates all database tables for Eva

param(
    [switch]$CheckOnly  # Only check if DB is initialized, don't create
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Get project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ServerDir = Join-Path $ProjectRoot "server"

Set-Location $ServerDir

# Activate virtual environment
$VenvPath = Join-Path $ServerDir "venv"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

if (-not (Test-Path $ActivateScript)) {
    Write-Error "ERROR: Virtual environment not found at $VenvPath"
    exit 1
}

& $ActivateScript

# Python script location
$ScriptPath = Join-Path $PSScriptRoot "init_database.py"

# Run Python script
if ($CheckOnly) {
    $Output = python $ScriptPath --check-only 2>&1
    $ExitCode = $LASTEXITCODE

    if ($ExitCode -eq 0) {
        # Already initialized
        exit 0
    } elseif ($ExitCode -eq 2) {
        # Not initialized
        exit 2
    } else {
        # Error
        Write-Error $Output
        exit 1
    }
} else {
    # Initialize database
    Write-Info "Initializing database..."
    $Output = python $ScriptPath 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Success $Output
        exit 0
    } else {
        Write-Error $Output
        exit 1
    }
}
