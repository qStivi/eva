# Wait for Docker services to be healthy
# Polls PostgreSQL, Redis, and ChromaDB until all respond

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Configuration
$Timeout = 60  # seconds
$PollInterval = 2  # seconds
$StartTime = Get-Date

# Get project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DockerDir = Join-Path $ProjectRoot "docker"

# Service health check functions
function Test-PostgreSQL {
    try {
        $Result = docker-compose -f "$DockerDir\docker-compose.yml" exec -T postgres pg_isready -U user -d character_companion 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-Redis {
    try {
        $Result = docker-compose -f "$DockerDir\docker-compose.yml" exec -T redis redis-cli ping 2>$null
        return $Result -match "PONG"
    } catch {
        return $false
    }
}

function Test-ChromaDB {
    try {
        $Result = Invoke-WebRequest -Uri "http://localhost:8000/api/v2" -TimeoutSec 2 -UseBasicParsing 2>$null
        return $Result.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Main wait loop
$Services = @{
    "PostgreSQL" = $false
    "Redis" = $false
    "ChromaDB" = $false
}

Write-Info "Waiting for services to be healthy (timeout: ${Timeout}s)..."

while ($true) {
    $Elapsed = ((Get-Date) - $StartTime).TotalSeconds

    # Check timeout
    if ($Elapsed -gt $Timeout) {
        Write-Error "ERROR: Services failed to become healthy within ${Timeout}s"
        Write-Host ""
        Write-Info "Service status:"
        foreach ($Service in $Services.Keys) {
            $Status = if ($Services[$Service]) { "[OK]" } else { "[X]" }
            Write-Host "  $Status $Service"
        }
        Write-Host ""
        Write-Info "Troubleshooting:"
        Write-Host "  1. Check Docker logs: docker-compose -f docker\docker-compose.yml logs"
        Write-Host "  2. Restart Docker Desktop"
        Write-Host "  3. Run: docker-compose -f docker\docker-compose.yml down -v; docker-compose -f docker\docker-compose.yml up -d"
        exit 1
    }

    # Test each service
    $Services["PostgreSQL"] = Test-PostgreSQL
    $Services["Redis"] = Test-Redis
    $Services["ChromaDB"] = Test-ChromaDB

    # Check if all healthy
    $AllHealthy = $true
    foreach ($Healthy in $Services.Values) {
        if (-not $Healthy) {
            $AllHealthy = $false
            break
        }
    }

    if ($AllHealthy) {
        Write-Success "[OK] All services healthy!"
        foreach ($Service in $Services.Keys) {
            Write-Host "  [OK] $Service" -ForegroundColor Green
        }
        exit 0
    }

    # Show progress
    $ReadyCount = ($Services.Values | Where-Object { $_ }).Count
    $TotalCount = $Services.Count
    Write-Host "`r  Waiting... ($ReadyCount/$TotalCount ready, ${Elapsed}s elapsed)" -NoNewline

    Start-Sleep -Seconds $PollInterval
}
