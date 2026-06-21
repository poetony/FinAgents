# TradingAgents-CN Portable - Start Backend Only
# This script starts only the Backend service (FastAPI + Uvicorn)
# Use this for manual backend startup or debugging

$ErrorActionPreference = "Continue"
$root = $PSScriptRoot

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  TradingAgents-CN - Start Backend Only" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Load .env file
function Load-Env($path) {
    $map = @{}
    if (Test-Path -LiteralPath $path) {
        foreach ($line in Get-Content -LiteralPath $path) {
            if ($line -match '^\s*#') { continue }
            if ($line -match '^\s*$') { continue }
            $idx = $line.IndexOf('=')
            if ($idx -gt 0) {
                $key = $line.Substring(0, $idx).Trim()
                $val = $line.Substring($idx + 1).Trim()
                $map[$key] = $val
            }
        }
    }
    return $map
}

# Read configuration
$envPath = Join-Path $root '.env'
if (-not (Test-Path $envPath)) {
    Write-Host "ERROR: .env file not found at: $envPath" -ForegroundColor Red
    exit 1
}

$envMap = Load-Env $envPath
$backendPort = if ($envMap.ContainsKey('PORT')) { [int]$envMap['PORT'] } else { 8000 }

Write-Host "Configuration:" -ForegroundColor White
Write-Host "  Backend Port: $backendPort" -ForegroundColor Gray
Write-Host ""

# Check if MongoDB and Redis are running
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$mongoRunning = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
$redisRunning = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue

if (-not $mongoRunning) {
    Write-Host "  WARNING: MongoDB is not running!" -ForegroundColor Yellow
    Write-Host "  Backend may fail to start without MongoDB" -ForegroundColor Yellow
}

if (-not $redisRunning) {
    Write-Host "  WARNING: Redis is not running!" -ForegroundColor Yellow
    Write-Host "  Backend may fail to start without Redis" -ForegroundColor Yellow
}

if ($mongoRunning -and $redisRunning) {
    Write-Host "  MongoDB and Redis are running" -ForegroundColor Green
}
Write-Host ""

# Check if port is in use
Write-Host "Checking port $backendPort..." -ForegroundColor Yellow
$portInUse = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "  WARNING: Port $backendPort is already in use!" -ForegroundColor Yellow
    foreach ($conn in $portInUse) {
        $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "    Process: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Gray
            Write-Host "    Path: $($process.Path)" -ForegroundColor Gray
        }
    }
    Write-Host ""
    $response = Read-Host "Stop existing process and continue? (Y/n)"
    if ($response -eq "" -or $response -eq "Y" -or $response -eq "y") {
        foreach ($conn in $portInUse) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
        Write-Host "  Existing process stopped" -ForegroundColor Green
    } else {
        Write-Host "  Cancelled by user" -ForegroundColor Yellow
        exit 0
    }
}
Write-Host ""

# Find Python executable
$pythonExe = Join-Path $root 'vendors\python\python.exe'
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python executable not found at: $pythonExe" -ForegroundColor Red
    exit 1
}

# Find app main
$appMain = Join-Path $root 'app\__main__.py'
if (-not (Test-Path $appMain)) {
    Write-Host "ERROR: app\__main__.py not found at: $appMain" -ForegroundColor Red
    exit 1
}

# Set UTF-8 encoding
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Host "Starting Backend..." -ForegroundColor Yellow
Write-Host "  Python: $pythonExe" -ForegroundColor Gray
Write-Host "  App: $appMain" -ForegroundColor Gray
Write-Host "  Port: $backendPort" -ForegroundColor Gray
Write-Host ""

# Start backend in foreground (not hidden, so you can see output)
Write-Host "Backend output:" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Gray
Write-Host ""

try {
    & $pythonExe $appMain
} catch {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Red
    Write-Host "ERROR: Backend crashed!" -ForegroundColor Red
    Write-Host "============================================================================" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

