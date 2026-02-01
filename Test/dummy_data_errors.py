#!/usr/bin/env python3
"""
Smart-Car Dummy Error Sender für ein bestimmtes Fahrzeug
Schreibt Fehler in das Measurement 'vehicle_errors'
"""

import argparse
import random
import paho.mqtt.client as mqtt

def main():
    parser = argparse.ArgumentParser(description="Sende Fehler nur für eine bestimmte Vehicle ID")
    parser.add_argument('--vehicle-id', '-v', required=True, help='Fahrzeug-ID, für die Fehler gesendet werden sollen')
    parser.add_argument('--broker', '-b', default='localhost', help='MQTT Broker')
    parser.add_argument('--port', '-p', type=int, default=1883, help='MQTT Port')
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
    except Exception as e:
        print(f"FEHLER: Verbindung zu {args.broker}:{args.port} fehlgeschlagen: {e}")
        exit(1)

    print(f"Sende Fehler für Fahrzeug: {args.vehicle_id}")
    error_codes = ["P0300", "P0420", "P0171", "P0455", "B1234"]
    error_code = random.choice(error_codes)
    payload = f"error,{args.vehicle_id},{error_code},1"

    try:
        print("Sende eine einzelne aktive Fehlermeldung...")
        info = client.publish(f"smartcar/{args.vehicle_id}", payload, qos=1)
        info.wait_for_publish()
        print(f"[SEND] {payload}")
        print("Fehler bleibt aktiv. Skript beendet.")
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
