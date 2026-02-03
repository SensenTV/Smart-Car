#!/usr/bin/env pwsh

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Smart-Car Docker Starter" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Überprüfe Docker..." -ForegroundColor Yellow
$null = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker läuft nicht oder ist nicht erreichbar!" -ForegroundColor Red
    exit 1
}
Write-Host "Docker läuft" -ForegroundColor Green

# Stoppe alte Container + entferne verwaiste Container
Write-Host "[2/4] Stoppe alte Container..." -ForegroundColor Yellow
docker-compose down --remove-orphans 2>&1 | Out-Null
Write-Host "Alte Container gestoppt" -ForegroundColor Green

# Starte neue Container mit minimaler Ausgabe
Write-Host "[3/4] Starte neue Container..." -ForegroundColor Yellow
$env:COMPOSE_PROGRESS = "plain"
docker-compose up -d 2>&1 | Select-String "Container|Network|Started|Created|Healthy" | ForEach-Object { Write-Host "  $_" }

# Warte auf Gesundheit der Services
Write-Host "[4/4] Warte auf Services..." -ForegroundColor Yellow
$maxWait = 120
for ($i = 0; $i -lt $maxWait; $i += 2) {
    $healthy = (docker-compose ps --format "{{.Name}} {{.State}}" 2>$null | Select-String "running|healthy").Count
    if ($healthy -ge 5) {
        break
    }
    Write-Host "Warte auf Services..." -NoNewline
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
