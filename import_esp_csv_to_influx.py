#!/usr/bin/env python3
"""
Importiert lokal gespeicherte ESP-Daten (CSV) in die InfluxDB für Grafana.
"""
import os
import csv
import sys
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

# InfluxDB Konfiguration (wie in auto_sync.py)
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "vehicle-admin-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "vehicle_org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vehicle_data")

CSV_FILE = "empfangene_can_daten.csv"

def parse_time(timestr):
    try:
        return datetime.strptime(timestr, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.utcnow()

def import_csv_to_influx():
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    imported = 0
    errors = 0
    fname = CSV_FILE
    if not os.path.isfile(fname):
        print(f"Datei nicht gefunden: {fname}")
        return
    
    from datetime import timedelta
    base_time = datetime.utcnow()
    
    with open(fname, newline='', encoding='utf-8') as f:
        reader = list(csv.reader(f))
        total = len(reader)
        print(f"Importiere {total} Zeilen aus {fname}...")
        
        for idx, row in enumerate(reader):
            # Leere oder zu kurze Zeilen überspringen
            if not row or len(row) < 2:
                continue
            try:
                # Zeitstempel: Verteile Datenpunkte über die letzte Stunde
                ts = base_time - timedelta(seconds=(total - idx) * 30)
                
                # Falls Zeitstempel in Daten vorhanden
                if len(row) > 0 and len(row[0]) > 8 and ("-" in row[0] or ":" in row[0]):
                    ts = parse_time(row[0])
                    row = row[1:]  # Zeitspalte entfernen
                
                mtype = row[0].lower()
                point = None
                
                if mtype == "state" and len(row) >= 5:
                    # Nutze vehicle_state für Dashboard-Kompatibilität
                    point = Point("vehicle_state") \
                        .tag("vehicle_id", row[1]) \
                        .field("state", row[2]) \
                        .field("fuel_l", float(row[3])) \
                        .field("battery_v", float(row[4])) \
                        .time(ts)
                        
                elif mtype == "gps" and len(row) >= 5:
                    point = Point("vehicle_gps") \
                        .tag("vehicle_id", row[1]) \
                        .field("lat", float(row[2])) \
                        .field("lon", float(row[3])) \
                        .field("speed", int(row[4]) if len(row) > 4 else 0) \
                        .time(ts)
                        
                elif mtype == "error" and len(row) >= 4:
                    # Nutze vehicle_errors für Dashboard-Kompatibilität
                    point = Point("vehicle_errors") \
                        .tag("vehicle_id", row[1]) \
                        .tag("error_code", row[2]) \
                        .field("active", int(row[3])) \
                        .time(ts)
                        
                elif mtype == "trip" and len(row) >= 7:
                    # Nutze trip_summary für Dashboard-Kompatibilität
                    point = Point("trip_summary") \
                        .tag("vehicle_id", row[1]) \
                        .tag("trip_id", row[2]) \
                        .field("duration_s", float(row[3])) \
                        .field("fuel_used", float(row[4])) \
                        .field("max_acceleration", float(row[5])) \
                        .field("max_braking", float(row[6])) \
                        .time(ts)
                        
                elif mtype == "alert" and len(row) >= 4:
                    point = Point("vehicle_alert") \
                        .tag("vehicle_id", row[1]) \
                        .field("alert_type", row[2]) \
                        .field("msg", row[3]) \
                        .time(ts)
                
                if point:
                    write_api.write(bucket=INFLUX_BUCKET, record=point)
                    imported += 1
                    if imported % 20 == 0:
                        print(f"  Fortschritt: {imported}/{total} importiert...")
                        
            except Exception as e:
                errors += 1
                print(f"Fehler Zeile {idx+1}: {e}")
                
    client.close()
    print(f"\nFertig! {imported} Datensätze importiert, {errors} Fehler.")

if __name__ == "__main__":
    import_csv_to_influx()
