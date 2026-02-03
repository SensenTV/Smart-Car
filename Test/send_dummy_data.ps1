# ============================================================
# Smart-Car Dummy Data Sender (PowerShell)
# ============================================================
# Sendet Testdaten an den MQTT Broker ohne ESP32 Hardware
# Verwendung: .\send_dummy_data.ps1 [-VehicleId "TEST001"] [-Type "state"]
# ============================================================

param(
    [string]$VehicleId = "TEST001",
    [string]$Type = "all",
    [string]$Broker = "localhost",
    [int]$Port = 1883,
    [switch]$Continuous,
    [int]$IntervalSeconds = 5
)

# Prüfe ob Mosquitto-Client installiert ist
$mosquittoPub = Get-Command "mosquitto_pub" -ErrorAction SilentlyContinue
if (-not $mosquittoPub) {
    Write-Host "WARNUNG: mosquitto_pub nicht gefunden. Installiere Mosquitto oder nutze Docker:" -ForegroundColor Yellow
    Write-Host "  docker exec smartcar-mosquitto mosquitto_pub ..." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Alternativ: Starte Node-RED (http://localhost:1880) und nutze die Inject-Nodes!" -ForegroundColor Green
    exit 1
}

function Get-RandomState {
    $states = @("idle", "driving", "parked", "charging")
    return $states[(Get-Random -Maximum $states.Count)]
}

function Get-RandomFuel {
    return [math]::Round((Get-Random -Minimum 10.0 -Maximum 55.0), 1)
}

function Get-RandomBattery {
    return [math]::Round((Get-Random -Minimum 11.5 -Maximum 14.2), 2)
}

function Send-StateData {
    param([string]$vid)
    $state = Get-RandomState
    $fuel = Get-RandomFuel
    $battery = Get-RandomBattery
    $payload = "state,$vid,$state,$fuel,$battery"
    $topic = "smartcar/$vid"
    
    Write-Host "[STATE] Sende: $payload" -ForegroundColor Cyan
    & mosquitto_pub -h $Broker -p $Port -t $topic -m $payload
}

function Send-ErrorData {
    param([string]$vid)
    $errorCodes = @("P0300", "P0420", "P0171", "P0455", "B1234", "C0035")
    $errorCode = $errorCodes[(Get-Random -Maximum $errorCodes.Count)]
    $active = Get-Random -Maximum 2
    $payload = "error,$vid,$errorCode,$active"
    $topic = "smartcar/$vid"
    
    Write-Host "[ERROR] Sende Fehler: $payload" -ForegroundColor Yellow
    & mosquitto_pub -h $Broker -p $Port -t $topic -m $payload
}

function Send-TripData {
    param([string]$vid)
    $tripId = "TRIP_" + (Get-Date -Format "yyyyMMdd_HHmmss")
    $duration = Get-Random -Minimum 300 -Maximum 3600
    $fuelUsed = [math]::Round((Get-Random -Minimum 1.5 -Maximum 8.0), 2)
    $maxAccel = [math]::Round((Get-Random -Minimum 2.5 -Maximum 6.0), 2)
    $maxBrake = [math]::Round((Get-Random -Minimum 3.0 -Maximum 8.0), 2)
    $payload = "trip,$vid,$tripId,$duration,$fuelUsed,$maxAccel,$maxBrake"
    $topic = "smartcar/$vid"
    
    Write-Host "[TRIP ] Sende Fahrt: $payload" -ForegroundColor Green
    & mosquitto_pub -h $Broker -p $Port -t $topic -m $payload
}

function Send-GpsData {
    param([string]$vid)
    # Koordinaten im Bereich Hamburg
    $lat = [math]::Round((Get-Random -Minimum 53.4 -Maximum 53.7), 6)
    $lon = [math]::Round((Get-Random -Minimum 9.8 -Maximum 10.2), 6)
    $speed = Get-Random -Minimum 0 -Maximum 130
    $payload = "gps,$vid,$lat,$lon,$speed"
    $topic = "smartcar/$vid"
    
    Write-Host "[GPS  ] Sende GPS: $payload" -ForegroundColor Magenta
    & mosquitto_pub -h $Broker -p $Port -t $topic -m $payload
}

function Send-AllData {
    param([string]$vid)
    Send-StateData -vid $vid
    Start-Sleep -Milliseconds 500
    if ((Get-Random -Maximum 10) -lt 2) {
        Send-ErrorData -vid $vid
        Start-Sleep -Milliseconds 500
    }
    Send-GpsData -vid $vid
}

# Hauptlogik
Write-Host "============================================" -ForegroundColor White
Write-Host "   Smart-Car Dummy Data Sender" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor White
Write-Host "Fahrzeug-ID: $VehicleId" -ForegroundColor Gray
Write-Host "Broker: $Broker`:$Port" -ForegroundColor Gray
Write-Host "Modus: $(if ($Continuous) { 'Kontinuierlich (alle ' + $IntervalSeconds + 's)' } else { 'Einmalig' })" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor White
Write-Host ""

if ($Continuous) {
    Write-Host "Drücke Ctrl+C zum Beenden..." -ForegroundColor Yellow
    Write-Host ""
    
    while ($true) {
        switch ($Type) {
            "state" { Send-StateData -vid $VehicleId }
            "error" { Send-ErrorData -vid $VehicleId }
            "trip"  { Send-TripData -vid $VehicleId }
            "gps"   { Send-GpsData -vid $VehicleId }
            "all"   { Send-AllData -vid $VehicleId }
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
} else {
    switch ($Type) {
        "state" { Send-StateData -vid $VehicleId }
        "error" { Send-ErrorData -vid $VehicleId }
        "trip"  { Send-TripData -vid $VehicleId }
        "gps"   { Send-GpsData -vid $VehicleId }
        "all"   { 
            Send-StateData -vid $VehicleId
            Send-GpsData -vid $VehicleId
            Write-Host ""
            Write-Host "Für Fehler: .\send_dummy_data.ps1 -Type error" -ForegroundColor Gray
            Write-Host "Für Fahrt:  .\send_dummy_data.ps1 -Type trip" -ForegroundColor Gray
            Write-Host "Kontinuierlich: .\send_dummy_data.ps1 -Continuous" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "Fertig! Pruefen der Daten in:" -ForegroundColor Green
Write-Host "   - Node-RED: http://localhost:1880" -ForegroundColor Gray
Write-Host "   - Grafana:  http://localhost:3001" -ForegroundColor Gray
