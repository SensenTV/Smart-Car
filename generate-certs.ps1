# PowerShell Script to generate TLS certificates for Mosquitto
# Requirements: OpenSSL muss installiert sein (z.B. via Git Bash oder WSL)

$CertDir = ".\mosquitto\config\certs"

# Create certificate directory
if (-not (Test-Path $CertDir)) {
    New-Item -ItemType Directory -Path $CertDir -Force | Out-Null
    Write-Host "Zertifikate-Verzeichnis erstellt: $CertDir"
}

# Check if OpenSSL is available
$opensslPath = Get-Command openssl -ErrorAction SilentlyContinue

if (-not $opensslPath) {
    Write-Host "Fehler: OpenSSL nicht gefunden!" -ForegroundColor Red
    Write-Host "Bitte installieren Sie OpenSSL über:" -ForegroundColor Yellow
    Write-Host "1. Git Bash (mit OpenSSL enthalten)" -ForegroundColor Yellow
    Write-Host "2. WSL (Windows Subsystem for Linux)" -ForegroundColor Yellow
    Write-Host "3. Chocolatey: choco install openssl" -ForegroundColor Yellow
    exit 1
}

Write-Host "Generiere TLS Zertifikate..." -ForegroundColor Green

# Generate private key
Write-Host "1. Generiere Private Key..."
openssl genrsa -out "$CertDir\mosquitto.key" 2048

# Generate self-signed certificate (gültig für 10 Jahre)
Write-Host "2. Generiere selbstsigniertes Zertifikat..."
openssl req -new -x509 -key "$CertDir\mosquitto.key" -out "$CertDir\mosquitto.crt" -days 3650 `
    -subj "/C=DE/ST=Berlin/L=Berlin/O=SmartCar/CN=mosquitto"

# Generate CA cert (same as cert for self-signed)
Write-Host "3. Kopiere CA Zertifikat..."
Copy-Item "$CertDir\mosquitto.crt" "$CertDir\ca.crt"

Write-Host "`nTLS Zertifikate erfolgreich erstellt!" -ForegroundColor Green
Write-Host "Dateien:"
Get-ChildItem $CertDir -File | ForEach-Object { Write-Host "  - $($_.Name)" }

Write-Host "`nNächste Schritte:" -ForegroundColor Cyan
Write-Host "1. Starten Sie die Container: docker-compose up -d" -ForegroundColor Cyan
Write-Host "2. Prüfen Sie die Logs: docker logs mosquitto" -ForegroundColor Cyan
