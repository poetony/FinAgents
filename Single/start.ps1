# Single 单股分析 - 一键启动前后端
# 在 Single 目录下执行: .\start.ps1

$ErrorActionPreference = "Stop"
$SingleDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SingleDir

Write-Host "=== Single 单股分析 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 启动后端 (8301)
Write-Host "[1/2] 启动后端 (端口 8301)..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "python" -ArgumentList "run_backend.py" -WorkingDirectory $SingleDir -PassThru -WindowStyle Normal
Start-Sleep -Seconds 3
if (-not $backendJob.HasExited) {
    Write-Host "  后端已启动 PID: $($backendJob.Id)" -ForegroundColor Green
} else {
    Write-Host "  后端启动可能失败，请检查日志" -ForegroundColor Red
}

# 2. 启动前端 (8302)
Write-Host "[2/2] 启动前端 (端口 8302)..." -ForegroundColor Yellow
if (Test-Path "node_modules") {
    $frontendJob = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $SingleDir -PassThru -WindowStyle Normal
    Start-Sleep -Seconds 2
    Write-Host "  前端已启动" -ForegroundColor Green
} else {
    Write-Host "  请先执行: npm install" -ForegroundColor Red
}

Write-Host ""
Write-Host "访问: http://localhost:8302" -ForegroundColor Cyan
Write-Host "API:  http://localhost:8301" -ForegroundColor Gray
