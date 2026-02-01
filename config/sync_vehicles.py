#!/usr/bin/env python3
"""
Lädt Fahrzeug-Stammdaten aus vehicles.json in InfluxDB.
Die Daten werden als Measurement 'vehicle_info' gespeichert.

Ausführen bei:
- Erstinstallation
- Änderungen an vehicles.json
- Sync auf neuen PC
"""

import json
import os
import sys
from datetime import datetime

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    print("FEHLER: influxdb-client nicht installiert!")
    print("Installiere mit: pip install influxdb-client")
    sys.exit(1)


# InfluxDB Konfiguration (gleich wie in docker-compose.yml)
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "vehicle-admin-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "vehicle_org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vehicle_data")

# Pfad zur vehicles.json
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VEHICLES_JSON = os.path.join(SCRIPT_DIR, "vehicles.json")


def load_vehicles_config():
    """Lädt die Fahrzeugkonfiguration aus JSON."""
    if not os.path.exists(VEHICLES_JSON):
        print(f"FEHLER: {VEHICLES_JSON} nicht gefunden!")
        sys.exit(1)
    
    with open(VEHICLES_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("vehicles", [])


def sync_to_influxdb(vehicles):
    """Schreibt Fahrzeug-Stammdaten in InfluxDB."""
    print(f"Verbinde zu InfluxDB: {INFLUX_URL}")
    
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        # Prüfe Verbindung
        health = client.health()
        if health.status != "pass":
            print(f"FEHLER: InfluxDB nicht gesund: {health.message}")
            sys.exit(1)
        
        print(f"InfluxDB OK - Version: {health.version}")
        
        # Schreibe jedes Fahrzeug
        for vehicle in vehicles:
            vid = vehicle.get("vehicle_id")
            if not vid:
                print("WARNUNG: Fahrzeug ohne vehicle_id übersprungen")
                continue
            
            # Erstelle Point mit allen Metadaten
            point = Point("vehicle_info") \
                .tag("vehicle_id", vid) \
                .field("display_name", vehicle.get("display_name", vid)) \
                .field("manufacturer", vehicle.get("manufacturer", "Unbekannt")) \
                .field("model", vehicle.get("model", "Unbekannt")) \
                .field("year", vehicle.get("year", 0)) \
                .field("license_plate", vehicle.get("license_plate", "")) \
                .field("fuel_capacity_l", vehicle.get("fuel_capacity_l", 50)) \
                .field("notes", vehicle.get("notes", ""))
            
            write_api.write(bucket=INFLUX_BUCKET, record=point)
            print(f"  ✓ {vid}: {vehicle.get('display_name', vid)}")
        
        client.close()
        print(f"\n{len(vehicles)} Fahrzeuge synchronisiert!")
        return True
        
    except Exception as e:
        print(f"FEHLER: {e}")
        return False


def main():
    print("=" * 50)
    print("Smart-Car Fahrzeug-Sync")
    print("=" * 50)
    print()
    
    # Lade Konfiguration
    vehicles = load_vehicles_config()
    print(f"Gefunden: {len(vehicles)} Fahrzeuge in vehicles.json")
    print()
    
    # Sync zu InfluxDB
    success = sync_to_influxdb(vehicles)
    
    if success:
        print()
        print("Fertig! Die Dashboards zeigen jetzt die Fahrzeugnamen.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
