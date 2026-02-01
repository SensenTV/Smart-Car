#!/usr/bin/env python3
"""
Auto-Sync für Fahrzeug-Stammdaten.
Wird beim Docker-Start automatisch ausgeführt.
"""

import json
import os
import sys
import time

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    print("influxdb-client wird installiert...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "influxdb-client", "-q"])
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS


# InfluxDB Konfiguration aus Umgebungsvariablen
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "vehicle-admin-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "vehicle_org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vehicle_data")

# Pfad zur vehicles.json (im Container gemountet)
VEHICLES_JSON = os.getenv("VEHICLES_JSON", "/config/vehicles.json")


def wait_for_influxdb(max_retries=30, delay=2):
    """Wartet bis InfluxDB bereit ist."""
    print(f"Warte auf InfluxDB ({INFLUX_URL})...")
    
    for i in range(max_retries):
        try:
            client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
            health = client.health()
            if health.status == "pass":
                print(f"InfluxDB bereit (Version: {health.version})")
                client.close()
                return True
            client.close()
        except Exception as e:
            pass
        
        print(f"  Versuch {i+1}/{max_retries}...")
        time.sleep(delay)
    
    print("FEHLER: InfluxDB nicht erreichbar!")
    return False


def load_vehicles():
    """Lädt Fahrzeugkonfiguration aus JSON."""
    if not os.path.exists(VEHICLES_JSON):
        print(f"WARNUNG: {VEHICLES_JSON} nicht gefunden - überspringe Sync")
        return []
    
    with open(VEHICLES_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("vehicles", [])


def sync_vehicles(vehicles):
    """Schreibt Fahrzeugdaten in InfluxDB."""
    if not vehicles:
        return True
    
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        for vehicle in vehicles:
            vid = vehicle.get("vehicle_id")
            if not vid:
                continue
            
            point = Point("vehicle_info") \
                .tag("vehicle_id", vid) \
                .field("display_name", vehicle.get("display_name", vid)) \
                .field("manufacturer", vehicle.get("manufacturer", "Unbekannt")) \
                .field("model", vehicle.get("model", "Unbekannt")) \
                .field("year", vehicle.get("year", 0)) \
                .field("license_plate", vehicle.get("license_plate", "")) \
                .field("vin", vehicle.get("vin", "")) \
                .field("fuel_capacity_l", vehicle.get("fuel_capacity_l", 50)) \
                .field("fuel_type", vehicle.get("fuel_type", "Benzin")) \
                .field("color", vehicle.get("color", "")) \
                .field("notes", vehicle.get("notes", ""))
            
            write_api.write(bucket=INFLUX_BUCKET, record=point)
            print(f"  ✓ {vid}: {vehicle.get('display_name', vid)}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"FEHLER beim Sync: {e}")
        return False


def main():
    print("=" * 50)
    print("Smart-Car Auto-Sync")
    print("=" * 50)
    
    # Warte auf InfluxDB
    if not wait_for_influxdb():
        sys.exit(1)
    
    # Lade und synchronisiere Fahrzeuge
    vehicles = load_vehicles()
    print(f"\nGefunden: {len(vehicles)} Fahrzeuge")
    
    if vehicles:
        if sync_vehicles(vehicles):
            print(f"\n✓ {len(vehicles)} Fahrzeuge synchronisiert!")
        else:
            sys.exit(1)
    else:
        print("Keine Fahrzeuge zum Synchronisieren.")
    
    print("Auto-Sync abgeschlossen.")


if __name__ == "__main__":
    main()
