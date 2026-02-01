#!/bin/bash
# Smart-Car Docker Compose Starter Script
# Startet alle Docker Container mit minimal Ausgabe

echo "================================================="
echo "Smart-Car Docker Starter"
echo "================================================="
echo ""

# Prüfe ob Docker läuft
echo "[1/4] Überprüfe Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "✗ Docker läuft nicht!"
    exit 1
fi
echo "✓ Docker läuft"

# Stoppe alte Container
echo "[2/4] Stoppe alte Container..."
docker-compose down > /dev/null 2>&1
echo "✓ Alte Container gestoppt"

# Starte neue Container mit minimaler Ausgabe
echo "[3/4] Starte neue Container..."
docker-compose up -d --quiet-pull 2>&1 | grep -E "Container|Network" | sed 's/^/  /'

# Warte auf Gesundheit der Services
echo "[4/4] Warte auf Services..."
max_wait=60
elapsed=0
healthy=0

while [ $healthy -lt 2 ] && [ $elapsed -lt $max_wait ]; do
    healthy=$(docker-compose ps --services --filter "status=running" 2>&1 | grep -E "mosquitto|influxdb" | wc -l)
    
    if [ $healthy -lt 2 ]; then
        printf "  ⏳ Warte auf Services (${elapsed}s)...\r"
        sleep 2
        elapsed=$((elapsed + 2))
    fi
done

# Finale Status
echo ""
echo "================================================="
echo "Service Status:"
echo "================================================="
docker-compose ps --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "✓ Alle Services gestartet!"
echo ""
echo "URLs:"
echo "  - Grafana:       http://localhost:3001"
echo "  - Node-RED:      http://localhost:1880"
echo "  - InfluxDB:      http://localhost:8086"
echo "  - Calendar:      http://localhost:5000/health"
echo ""
