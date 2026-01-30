#!/usr/bin/env python3
"""
Smart-Car Dummy Error Sender für ein bestimmtes Fahrzeug
Schreibt Fehler in das Measurement 'vehicle_errors'
"""

import argparse
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

def main():
    parser = argparse.ArgumentParser(description="Sende Fehler nur für eine bestimmte Vehicle ID")
    parser.add_argument('--vehicle-id', '-v', required=True, help='Fahrzeug-ID, für die Fehler gesendet werden sollen')
    parser.add_argument('--broker', '-b', default='localhost', help='MQTT Broker')
    parser.add_argument('--port', '-p', type=int, default=1883, help='MQTT Port')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Intervall in Sekunden zwischen Fehlern')
    args = parser.parse_args()

    client = mqtt.Client()
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
    except Exception as e:
        print(f"FEHLER: Verbindung zu {args.broker}:{args.port} fehlgeschlagen: {e}")
        exit(1)

    print(f"Sende Fehler für Fahrzeug: {args.vehicle_id}")
    error_codes = ["P0300", "P0420", "P0171", "P0455", "B1234"]
    iteration = 0

    try:
        while True:
            iteration += 1
            error_code = random.choice(error_codes)
            timestamp = datetime.utcnow().isoformat() + "Z"

            # Fehler aktivieren
            # Measurement = vehicle_errors, Tag = vehicle_id, Fields = error_code + active, Time = jetzt
            payload_active = f"vehicle_errors,vehicle_id={args.vehicle_id} error_code=\"{error_code}\",active=1 {int(time.time()*1e9)}"
            client.publish(f"smartcar/{args.vehicle_id}/errors", payload_active)
            print(f"[SEND] {payload_active}")

            # Nach 3 Sekunden deaktivieren
            time.sleep(3)
            payload_inactive = f"vehicle_errors,vehicle_id={args.vehicle_id} error_code=\"{error_code}\",active=0 {int(time.time()*1e9)}"
            client.publish(f"smartcar/{args.vehicle_id}/errors", payload_inactive)
            print(f"[SEND] {payload_inactive}")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
