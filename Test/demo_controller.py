#!/usr/bin/env python3
"""
Smart-Car Demo Controller
=========================
Interaktives Tool fuer Live-Demonstrationen.
Ermoeglicht das schnelle Ausloesen von Ereignissen in Grafana.
"""

import paho.mqtt.client as mqtt
import time
import random
import sys
from datetime import datetime

# Konfiguration
BROKER = "localhost"
PORT = 1883
VEHICLE_ID = "TEST001"

# MQTT Client
client = mqtt.Client(client_id="demo-controller")

def connect():
    """Verbinde mit MQTT Broker."""
    try:
        client.connect(BROKER, PORT, 60)
        print(f"[OK] Verbunden mit {BROKER}:{PORT}")
        return True
    except Exception as e:
        print(f"[FEHLER] Verbindung fehlgeschlagen: {e}")
        return False

def send(topic, payload):
    """Sende MQTT Nachricht."""
    full_topic = f"smartcar/{VEHICLE_ID}"
    client.publish(full_topic, payload)
    print(f"[GESENDET] {payload}")

def trigger_error(code=None, active=True):
    """Loesche einen Fahrzeugfehler aus."""
    codes = ["P0300", "P0420", "P0171", "P0455", "P0128", "C0035", "B1234", "U0100"]
    error_code = code or random.choice(codes)
    active_val = 1 if active else 0
    send(f"smartcar/{VEHICLE_ID}", f"error,{VEHICLE_ID},{error_code},{active_val}")
    status = "AKTIV" if active else "GELOEST"
    print(f"    -> Fehler {error_code}: {status}")

def trigger_alert(alert_type=None, message=None):
    """Sende einen Alarm."""
    alerts = [
        ("fuel_low", "Kraftstoff_unter_10L"),
        ("battery_low", "Batterie_kritisch_unter_11V"),
        ("overspeed", "Geschwindigkeit_ueber_130kmh"),
        ("geofence", "Fahrzeug_ausserhalb_Gebiet"),
        ("maintenance", "Wartung_faellig"),
        ("crash", "Aufprall_erkannt"),
    ]
    if not alert_type:
        alert_type, message = random.choice(alerts)
    send(f"smartcar/{VEHICLE_ID}", f"alert,{VEHICLE_ID},{alert_type},{message}")
    print(f"    -> Alarm: {alert_type}")

def trigger_trip():
    """Beende eine Fahrt (Trip Summary)."""
    trip_id = f"TRIP_{datetime.now().strftime('%H%M%S')}"
    duration = random.randint(300, 7200)  # 5min - 2h
    fuel_used = round(random.uniform(2.0, 15.0), 2)
    max_acc = round(random.uniform(2.0, 6.0), 2)
    max_brake = round(random.uniform(3.0, 8.0), 2)
    send(f"smartcar/{VEHICLE_ID}", f"trip,{VEHICLE_ID},{trip_id},{duration},{fuel_used},{max_acc},{max_brake}")
    print(f"    -> Fahrt beendet: {duration}s, {fuel_used}L verbraucht")

def send_state(state=None, fuel=None, battery=None):
    """Sende Fahrzeugstatus."""
    states = ["idle", "driving", "parked", "charging"]
    state = state or random.choice(states)
    fuel = fuel or round(random.uniform(10, 55), 1)
    battery = battery or round(random.uniform(11.5, 14.0), 2)
    send(f"smartcar/{VEHICLE_ID}", f"state,{VEHICLE_ID},{state},{fuel},{battery}")
    print(f"    -> Status: {state}, Fuel: {fuel}L, Batterie: {battery}V")

def send_gps(lat=None, lon=None, speed=None):
    """Sende GPS Position."""
    lat = lat or round(53.55 + random.uniform(-0.1, 0.1), 6)
    lon = lon or round(10.0 + random.uniform(-0.1, 0.1), 6)
    speed = speed or random.randint(0, 120)
    send(f"smartcar/{VEHICLE_ID}", f"gps,{VEHICLE_ID},{lat},{lon},{speed}")
    print(f"    -> GPS: {lat}, {lon} @ {speed} km/h")

def demo_scenario_emergency():
    """Notfall-Szenario: Mehrere kritische Ereignisse."""
    print("\n[SZENARIO] Notfall-Simulation...")
    send_state("driving", 8.5, 11.2)
    time.sleep(0.5)
    trigger_error("P0300", True)
    time.sleep(0.5)
    trigger_alert("fuel_low", "Kraftstoff_kritisch_5L")
    time.sleep(0.5)
    trigger_alert("battery_low", "Batterie_unter_11V")
    print("[SZENARIO] Notfall abgeschlossen!\n")

def demo_scenario_normal_day():
    """Normaler Tag: Fahrt starten, fahren, parken."""
    print("\n[SZENARIO] Normaler Arbeitstag...")
    send_state("idle", 45.0, 12.8)
    time.sleep(1)
    send_state("driving", 44.5, 12.6)
    send_gps(53.55, 10.0, 50)
    time.sleep(1)
    send_state("driving", 42.0, 12.5)
    send_gps(53.56, 10.02, 80)
    time.sleep(1)
    send_state("parked", 40.0, 12.7)
    trigger_trip()
    print("[SZENARIO] Tag abgeschlossen!\n")

def demo_scenario_error_resolve():
    """Fehler auftauchen und beheben."""
    print("\n[SZENARIO] Fehler-Behebung...")
    trigger_error("P0420", True)
    print("    ... warte 3 Sekunden ...")
    time.sleep(3)
    trigger_error("P0420", False)
    print("[SZENARIO] Fehler behoben!\n")

def print_menu():
    """Zeige Hauptmenue."""
    print("\n" + "="*50)
    print("   SMART-CAR DEMO CONTROLLER")
    print("="*50)
    print(f"   Fahrzeug: {VEHICLE_ID}")
    print("="*50)
    print("\n[EINZELNE EREIGNISSE]")
    print("  1 - Fehler ausloesen (zufaellig)")
    print("  2 - Fehler beheben (zufaellig)")
    print("  3 - Alarm senden")
    print("  4 - Fahrt beenden")
    print("  5 - Status senden")
    print("  6 - GPS senden")
    print("\n[SZENARIEN]")
    print("  7 - Notfall-Szenario (mehrere Alarme)")
    print("  8 - Normaler Tag (Fahrt simulieren)")
    print("  9 - Fehler auftreten + beheben")
    print("\n[SPEZIELLE FEHLER]")
    print("  p - Motor-Fehler P0300")
    print("  c - Katalysator P0420")
    print("  b - Batterie-Fehler B1234")
    print("\n[SPEZIELLE ALARME]")
    print("  f - Kraftstoff niedrig")
    print("  s - Geschwindigkeit zu hoch")
    print("  g - Geofence-Verletzung")
    print("\n  0 - Beenden")
    print("="*50)

def main():
    """Hauptprogramm."""
    print("\nVerbinde mit MQTT Broker...")
    if not connect():
        sys.exit(1)
    
    while True:
        print_menu()
        choice = input("\nAuswahl: ").strip().lower()
        
        if choice == "0":
            print("\nAuf Wiedersehen!")
            break
        elif choice == "1":
            trigger_error(active=True)
        elif choice == "2":
            trigger_error(active=False)
        elif choice == "3":
            trigger_alert()
        elif choice == "4":
            trigger_trip()
        elif choice == "5":
            send_state()
        elif choice == "6":
            send_gps()
        elif choice == "7":
            demo_scenario_emergency()
        elif choice == "8":
            demo_scenario_normal_day()
        elif choice == "9":
            demo_scenario_error_resolve()
        elif choice == "p":
            trigger_error("P0300", True)
        elif choice == "c":
            trigger_error("P0420", True)
        elif choice == "b":
            trigger_error("B1234", True)
        elif choice == "f":
            trigger_alert("fuel_low", "Kraftstoff_unter_10L")
        elif choice == "s":
            trigger_alert("overspeed", "Geschwindigkeit_130kmh_ueberschritten")
        elif choice == "g":
            trigger_alert("geofence", "Fahrzeug_ausserhalb_erlaubter_Zone")
        else:
            print("[?] Unbekannte Auswahl")
    
    client.disconnect()

if __name__ == "__main__":
    main()
