#!/usr/bin/env python3
"""
Smart-Car Dummy Data Sender
Sendet realistische Testdaten mit graduellen Wertaenderungen.
"""

import argparse
import random
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("FEHLER: paho-mqtt nicht installiert!")
    print("Installiere mit: pip install paho-mqtt")
    exit(1)


class VehicleSimulator:
    """Simuliert ein Fahrzeug mit realistischen Werten."""
    
    def __init__(self, vehicle_id: str):
        self.vehicle_id = vehicle_id
        self.fuel = random.uniform(30.0, 50.0)
        self.battery = random.uniform(12.5, 13.5)
        self.state = "idle"
        self.lat = 53.55  # Hamburg
        self.lon = 10.0
        self.speed = 0
        self.trip_counter = 0
        self.error_active = False
        self.error_code = None
        
    def update(self):
        """Aktualisiert Werte graduell."""
        # State wechseln (selten)
        if random.random() < 0.05:
            self.state = random.choice(["idle", "driving", "parked", "charging"])
        
        # Fuel - langsam sinken beim Fahren, leicht steigen beim Laden
        if self.state == "driving":
            self.fuel = max(5.0, self.fuel - random.uniform(0.1, 0.3))
        elif self.state == "charging":
            self.fuel = min(55.0, self.fuel + random.uniform(0.5, 1.5))
        else:
            self.fuel += random.uniform(-0.05, 0.05)
        
        # Battery - schwankt leicht
        if self.state == "driving":
            self.battery = max(11.8, self.battery - random.uniform(0.01, 0.05))
        elif self.state == "charging":
            self.battery = min(14.2, self.battery + random.uniform(0.02, 0.08))
        else:
            self.battery += random.uniform(-0.02, 0.02)
        
        # Clamp values
        self.fuel = max(5.0, min(55.0, self.fuel))
        self.battery = max(11.5, min(14.2, self.battery))
        
        # GPS - kleine Bewegungen
        if self.state == "driving":
            self.lat += random.uniform(-0.002, 0.002)
            self.lon += random.uniform(-0.002, 0.002)
            self.speed = random.randint(30, 100)
        else:
            self.speed = 0
            
        # Clamp GPS to Hamburg area
        self.lat = max(53.4, min(53.7, self.lat))
        self.lon = max(9.8, min(10.2, self.lon))
        
    def get_state_msg(self) -> str:
        return f"state,{self.vehicle_id},{self.state},{self.fuel:.1f},{self.battery:.2f}"
    
    def get_gps_msg(self) -> str:
        return f"gps,{self.vehicle_id},{self.lat:.6f},{self.lon:.6f},{self.speed}"
    
    def get_error_msg(self, active: bool = True) -> str:
        codes = ["P0300", "P0420", "P0171", "P0455", "B1234"]
        if active and not self.error_active:
            self.error_code = random.choice(codes)
            self.error_active = True
        elif not active:
            self.error_active = False
        return f"error,{self.vehicle_id},{self.error_code},{1 if active else 0}"
    
    def get_trip_msg(self) -> str:
        self.trip_counter += 1
        trip_id = f"TRIP_{self.vehicle_id}_{self.trip_counter:03d}"
        duration = random.randint(600, 3600)
        fuel_used = random.uniform(2.0, 8.0)
        max_acc = random.uniform(2.5, 5.0)
        max_brake = random.uniform(3.0, 6.0)
        return f"trip,{self.vehicle_id},{trip_id},{duration},{fuel_used:.2f},{max_acc:.2f},{max_brake:.2f}"
    
    def get_alert_msg(self, alert_type: str, message: str) -> str:
        return f"alert,{self.vehicle_id},{alert_type},{message}"


def main():
    parser = argparse.ArgumentParser(description='Smart-Car Dummy Data Sender')
    parser.add_argument('--vehicle-id', '-v', default='TEST001', help='Fahrzeug-ID')
    parser.add_argument('--broker', '-b', default='localhost', help='MQTT Broker')
    parser.add_argument('--port', '-p', type=int, default=1883, help='MQTT Port')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Interval in Sekunden')
    parser.add_argument('--continuous', '-c', action='store_true', help='Kontinuierlich senden')
    parser.add_argument('--with-errors', action='store_true', help='Auch Fehler generieren')
    parser.add_argument('--with-trips', action='store_true', help='Auch Fahrten generieren')
    parser.add_argument('--with-alerts', action='store_true', help='Auch Alarme generieren')
    parser.add_argument('--full-test', action='store_true', help='Alle Datentypen senden')
    
    args = parser.parse_args()
    
    if args.full_test:
        args.with_errors = True
        args.with_trips = True
        args.with_alerts = True
    
    # MQTT Client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
    except Exception as e:
        print(f"FEHLER: Verbindung zu {args.broker}:{args.port} fehlgeschlagen: {e}")
        print("Tipp: Starte Docker mit: docker-compose up -d")
        exit(1)
    
    print("=" * 50)
    print("   Smart-Car Dummy Data Sender")
    print("=" * 50)
    print(f"Broker: {args.broker}:{args.port}")
    print(f"Fahrzeug: {args.vehicle_id}")
    print(f"Modus: {'Kontinuierlich' if args.continuous else 'Einmalig'}")
    print(f"Fehler: {'Ja' if args.with_errors else 'Nein'}")
    print(f"Fahrten: {'Ja' if args.with_trips else 'Nein'}")
    print(f"Alarme: {'Ja' if args.with_alerts else 'Nein'}")
    print("=" * 50)
    print()
    
    sim = VehicleSimulator(args.vehicle_id)
    topic = f"smartcar/{args.vehicle_id}"
    iteration = 0
    
    def send(msg_type: str, payload: str):
        print(f"[{msg_type.upper():6}] {payload}")
        client.publish(topic, payload)
    
    try:
        if args.continuous:
            print("Druecke Ctrl+C zum Beenden...\n")
            while True:
                sim.update()
                iteration += 1
                
                # State und GPS immer senden
                send("state", sim.get_state_msg())
                time.sleep(0.3)
                send("gps", sim.get_gps_msg())
                
                # Fehler alle 10 Iterationen
                if args.with_errors and iteration % 10 == 0:
                    time.sleep(0.3)
                    # Fehler aktivieren
                    send("error", sim.get_error_msg(active=True))
                
                # Fehler deaktivieren nach 3 Iterationen
                if args.with_errors and iteration % 10 == 3 and sim.error_active:
                    time.sleep(0.3)
                    send("error", sim.get_error_msg(active=False))
                
                # Trip alle 20 Iterationen
                if args.with_trips and iteration % 20 == 0:
                    time.sleep(0.3)
                    send("trip", sim.get_trip_msg())
                
                # Alert bei niedrigem Kraftstoff
                if args.with_alerts and sim.fuel < 15:
                    time.sleep(0.3)
                    send("alert", sim.get_alert_msg("low_fuel", f"Kraftstoff_niedrig_{sim.fuel:.1f}L"))
                
                # Alert bei niedriger Batterie
                if args.with_alerts and sim.battery < 11.8:
                    time.sleep(0.3)
                    send("alert", sim.get_alert_msg("low_battery", f"Batterie_niedrig_{sim.battery:.2f}V"))
                
                time.sleep(args.interval)
        else:
            # Einmaliger Test
            send("state", sim.get_state_msg())
            time.sleep(0.3)
            send("gps", sim.get_gps_msg())
            
            if args.with_errors:
                time.sleep(0.3)
                send("error", sim.get_error_msg(active=True))
            
            if args.with_trips:
                time.sleep(0.3)
                send("trip", sim.get_trip_msg())
            
            if args.with_alerts:
                time.sleep(0.3)
                send("alert", sim.get_alert_msg("test", "Test_Alarm"))
            
            print("\nFertig! Pruefe Grafana: http://localhost:3001")
    
    except KeyboardInterrupt:
        print("\n\nBeendet.")
    
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
