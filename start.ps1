#!/usr/bin/env pwsh

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Smart-Car Docker Starter" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Prüfe ob Docker läuft
Write-Host "[1/4] Überprüfe Docker..." -ForegroundColor Yellow
if ((docker ps 2>&1 | Select-String "error") -or $LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker läuft nicht!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker läuft" -ForegroundColor Green

# Stoppe alte Container
Write-Host "[2/4] Stoppe alte Container..." -ForegroundColor Yellow
docker-compose down 2>&1 | Out-Null
Write-Host "✓ Alte Container gestoppt" -ForegroundColor Green

# Starte neue Container mit minimaler Ausgabe
Write-Host "[3/4] Starte neue Container..." -ForegroundColor Yellow
docker-compose up -d 2>&1 | Select-String "Container|Network" | ForEach-Object { Write-Host "  $_" }

# Warte auf Gesundheit der Services
Write-Host "[4/4] Warte auf Services..." -ForegroundColor Yellow
$maxWait = 60
$elapsed = 0

for ($i = 0; $i -lt $maxWait; $i += 2) {
    $running = (docker-compose ps --services --filter "status=running" 2>&1).Count
    if ($running -ge 5) {
        break
    }
    Write-Host "  ⏳ Warte auf Services..." -NoNewline
    Start-Sleep -Seconds 2
    Write-Host "`r" -NoNewline
}

# Finale Status
Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Service Status:" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
docker-compose ps --format "table {{.Names}}`t{{.Status}}"

Write-Host ""
Write-Host "Alle Services gestartet!" -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "  Grafana:  http://localhost:3001"
Write-Host "  Node-RED: http://localhost:1880"
Write-Host "  InfluxDB: http://localhost:8086"
Write-Host ""
