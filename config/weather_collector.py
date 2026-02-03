#!/usr/bin/env python3
"""
Weather Data Collector für Smart-Car
Holt periodisch Wetter- und Reifendaten und schreibt sie in InfluxDB.
"""

import os
import sys
import time
import requests
from datetime import datetime

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    print("influxdb-client wird installiert...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "influxdb-client", "-q"])
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS

# Konfiguration
WEATHER_SERVICE_URL = os.environ.get('WEATHER_SERVICE_URL', 'http://weather-service:5001')
TIRE_SERVICE_URL = os.environ.get('TIRE_SERVICE_URL', 'http://tire-service:5003')
INFLUX_URL = os.environ.get('INFLUX_URL', 'http://influxdb:8086')
INFLUX_TOKEN = os.environ.get('INFLUX_TOKEN', 'vehicle-admin-token')
INFLUX_ORG = os.environ.get('INFLUX_ORG', 'vehicle_org')
INFLUX_BUCKET = os.environ.get('INFLUX_BUCKET', 'vehicle_data')
COLLECT_INTERVAL = int(os.environ.get('COLLECT_INTERVAL', 300))  # 5 Minuten


def wait_for_services(max_retries=30, delay=5):
    """Wartet bis alle Services bereit sind."""
    services = [
        (WEATHER_SERVICE_URL + '/health', 'Weather-Service'),
        (TIRE_SERVICE_URL + '/health', 'Tire-Service'),
    ]
    
    for url, name in services:
        print(f"Warte auf {name}...")
        for i in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"  ✓ {name} bereit")
                    break
            except:
                pass
            time.sleep(delay)
        else:
            print(f"  ⚠ {name} nicht erreichbar - fahre trotzdem fort")


def collect_weather_data():
    """Holt Wetterdaten und schreibt sie in InfluxDB."""
    try:
        response = requests.get(f"{WEATHER_SERVICE_URL}/weather", timeout=10)
        if response.status_code != 200:
            print(f"Weather-API Fehler: {response.status_code}")
            return None
        
        data = response.json()
        
        if 'error' in data:
            print(f"Weather-API Error: {data['error']}")
            return None
        
        # InfluxDB Point erstellen
        point = Point("weather") \
            .tag("location", data.get('location_name', 'Unknown')) \
            .field("temperature_c", float(data.get('temperature_c', 0))) \
            .field("feels_like_c", float(data.get('feels_like_c', 0))) \
            .field("humidity_percent", float(data.get('humidity_percent', 0))) \
            .field("pressure_hpa", float(data.get('pressure_hpa', 0))) \
            .field("wind_speed_ms", float(data.get('wind_speed_ms', 0))) \
            .field("wind_direction_deg", float(data.get('wind_direction_deg', 0))) \
            .field("clouds_percent", float(data.get('clouds_percent', 0))) \
            .field("visibility_m", float(data.get('visibility_m', 10000))) \
            .field("weather_main", data.get('weather_main', 'Unknown')) \
            .field("weather_description", data.get('weather_description', ''))
        
        # Fahrbedingungen
        driving_conditions = data.get('driving_conditions', 3)
        point.field("driving_conditions", int(driving_conditions))
        point.field("driving_conditions_text", data.get('driving_conditions_text', 'Unbekannt'))
        
        return point
        
    except Exception as e:
        print(f"Fehler beim Sammeln der Wetterdaten: {e}")
        return None


def collect_tire_data():
    """Holt Reifenstatus und schreibt ihn in InfluxDB."""
    try:
        response = requests.get(f"{TIRE_SERVICE_URL}/tires/status", timeout=10)
        if response.status_code != 200:
            print(f"Tire-API Fehler: {response.status_code}")
            return []
        
        data = response.json()
        points = []
        
        recommendation = data.get('recommendation', {})
        
        for vehicle in data.get('vehicles', []):
            vehicle_id = vehicle.get('vehicle_id', 'unknown')
            
            # Status zu numerischem Wert
            status_map = {'ok': 0, 'warning': 1, 'critical': 2, 'unknown': -1}
            status_value = status_map.get(vehicle.get('status', 'unknown'), -1)
            
            # Reifentyp zu numerischem Wert (für Grafana Farben)
            tire_map = {'summer': 1, 'winter': 2, 'allseason': 3, 'unknown': 0}
            current_tires_value = tire_map.get(vehicle.get('current_tires', 'unknown'), 0)
            recommended_value = tire_map.get(recommendation.get('recommended', 'unknown'), 0)
            
            point = Point("tire_status") \
                .tag("vehicle_id", vehicle_id) \
                .tag("display_name", vehicle.get('display_name', vehicle_id)) \
                .field("current_tires", vehicle.get('current_tires', 'unknown')) \
                .field("current_tires_value", current_tires_value) \
                .field("tire_brand", vehicle.get('tire_brand', 'N/A')) \
                .field("tire_size", vehicle.get('tire_size', 'N/A')) \
                .field("status", vehicle.get('status', 'unknown')) \
                .field("status_value", status_value) \
                .field("status_text", vehicle.get('status_text', '')) \
                .field("recommended", recommendation.get('recommended', 'unknown')) \
                .field("recommended_value", recommended_value) \
                .field("recommendation_label", recommendation.get('label', ''))
            
            points.append(point)
        
        return points
        
    except Exception as e:
        print(f"Fehler beim Sammeln der Reifendaten: {e}")
        return []


def write_to_influx(points):
    """Schreibt Punkte in InfluxDB."""
    if not points:
        return False
    
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        if isinstance(points, list):
            for point in points:
                write_api.write(bucket=INFLUX_BUCKET, record=point)
        else:
            write_api.write(bucket=INFLUX_BUCKET, record=points)
        
        client.close()
        return True
        
    except Exception as e:
        print(f"InfluxDB Fehler: {e}")
        return False


def main():
    """Hauptschleife."""
    print("=" * 50)
    print("Smart-Car Weather & Tire Collector")
    print(f"Intervall: {COLLECT_INTERVAL} Sekunden")
    print("=" * 50)
    
    # Auf Services warten
    wait_for_services()
    
    print(f"\nStarte Sammlung alle {COLLECT_INTERVAL}s...")
    
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Wetterdaten sammeln
        weather_point = collect_weather_data()
        if weather_point:
            if write_to_influx(weather_point):
                temp = weather_point._fields.get('temperature_c', 'N/A')
                print(f"[{timestamp}] Wetter: {temp}°C ✓")
            else:
                print(f"[{timestamp}] Wetter: Schreibfehler ✗")
        else:
            print(f"[{timestamp}] Wetter: Keine Daten ✗")
        
        # Reifendaten sammeln
        tire_points = collect_tire_data()
        if tire_points:
            if write_to_influx(tire_points):
                print(f"[{timestamp}] Reifen: {len(tire_points)} Fahrzeuge ✓")
            else:
                print(f"[{timestamp}] Reifen: Schreibfehler ✗")
        else:
            print(f"[{timestamp}] Reifen: Keine Daten ✗")
        
        # Warten
        time.sleep(COLLECT_INTERVAL)


if __name__ == '__main__':
    main()
