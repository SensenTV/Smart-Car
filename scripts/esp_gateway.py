#!/usr/bin/env python3
"""
ESP32 Gateway
Empfängt CAN-Daten vom ESP32 per TCP und sendet sie direkt per MQTT weiter.
Speichert optional auch in CSV-Datei.
"""

import socket
import threading
import time
import os
import paho.mqtt.client as mqtt

# Konfiguration
SERVER_PORT = int(os.environ.get('ESP_PORT', 8080))
CSV_FILE = "/data/empfangene_can_daten.csv"
SAVE_TO_CSV = os.environ.get('SAVE_TO_CSV', 'true').lower() == 'true'
MQTT_BROKER = os.environ.get('MQTT_BROKER', 'mosquitto')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_TOPIC_PREFIX = "smartcar/"
ALLOWED_TEST_VEHICLE = "TEST001"
ALLOWED_VW_VEHICLE = "VW-Passat-B5-001"

# MQTT Client Setup  
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
mqtt_client = mqtt.Client()
mqtt_connected = False

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print(f"[OK] MQTT verbunden mit {MQTT_BROKER}:{MQTT_PORT}")
    else:
        mqtt_connected = False
        print(f"[ERROR] MQTT Verbindung fehlgeschlagen: {rc}")

mqtt_client.on_connect = on_connect

# Statistiken
stats = {
    'lines_received': 0,
    'lines_sent': 0,
    'errors': 0,
    'connections': 0
}

def send_to_mqtt(line):
    """Sendet eine Zeile per MQTT"""
    if not mqtt_connected:
        return False
    
    line = line.strip()
    if not line:
        return False
    
    try:
        parts = line.split(',')
        if len(parts) >= 2:
            vehicle_id = parts[1]
            if vehicle_id not in (ALLOWED_TEST_VEHICLE, ALLOWED_VW_VEHICLE):
                upper_id = vehicle_id.upper()
                if "VW" in upper_id or "PASSAT" in upper_id:
                    vehicle_id = ALLOWED_VW_VEHICLE
                else:
                    vehicle_id = ALLOWED_TEST_VEHICLE
                parts[1] = vehicle_id
                line = ",".join(parts)
            topic = f"{MQTT_TOPIC_PREFIX}{vehicle_id}"
            
            result = mqtt_client.publish(topic, line, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                stats['lines_sent'] += 1
                print(f"[OK] {vehicle_id}: {parts[0]}")
                return True
            else:
                stats['errors'] += 1
                print(f"[ERROR] MQTT Fehler für: {line[:50]}")
                return False
    except Exception as e:
        stats['errors'] += 1
        print(f"[ERROR] Fehler beim Senden: {e}")
        return False
    
    return False

def handle_client(conn, addr):
    """Behandelt eine ESP32-Verbindung"""
    stats['connections'] += 1
    print(f"[CONN] Verbindung #{stats['connections']} von {addr[0]}:{addr[1]}")
    
    csv_file = None
    if SAVE_TO_CSV:
        try:
            csv_file = open(CSV_FILE, 'a', encoding='utf-8')
            print(f"[FILE] Schreibe auch in {CSV_FILE}")
        except Exception as e:
            print(f"[WARNING] CSV-Datei konnte nicht geoeffnet werden: {e}")
    
    buffer = ""
    
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            # Daten dekodieren und zum Buffer hinzufügen
            buffer += data.decode('utf-8', errors='ignore')
            
            # Zeilen verarbeiten
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                
                if line:
                    stats['lines_received'] += 1
                    
                    # In CSV schreiben (wenn aktiviert)
                    if csv_file:
                        csv_file.write(line + '\n')
                        csv_file.flush()
                    
                    # Per MQTT senden
                    send_to_mqtt(line)
        
        print(f"[OK] Verbindung von {addr[0]} beendet ({stats['lines_received']} Zeilen)")
        
    except Exception as e:
        print(f"[ERROR] Fehler bei Verbindung {addr[0]}: {e}")
        stats['errors'] += 1
    
    finally:
        if csv_file:
            csv_file.close()
        conn.close()

def start_tcp_server():
    """Startet den TCP-Server für ESP32-Verbindungen"""
    
    # MQTT Verbindung aufbauen
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("[INFO] MQTT Client gestartet...")
        time.sleep(2)  # Kurz warten für Verbindungsaufbau
    except Exception as e:
        print(f"[WARNING] MQTT Verbindung fehlgeschlagen: {e}")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', SERVER_PORT))
    server_socket.listen(5)
    
    print(f"\n{'='*60}")
    print(f"[START] ESP32 Gateway gestartet")
    print(f"{'='*60}")
    print(f"[TCP]  Server:  0.0.0.0:{SERVER_PORT}")
    print(f"[MQTT] Broker:  {MQTT_BROKER}:{MQTT_PORT}")
    print(f"[FILE] CSV:     {'Aktiviert' if SAVE_TO_CSV else 'Deaktiviert'}")
    print(f"{'='*60}\n")
    
    # Auto-Load: Lade existierende CSV-Datei beim Start
    if os.path.exists(CSV_FILE) and mqtt_connected:
        print("[INFO] Lade vorhandene CSV-Datei...\n")
        try:
            with open(CSV_FILE, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line:
                        send_to_mqtt(line)
                        time.sleep(2.0)  # 2 Sekunden Verzoegerung zwischen Zeilen
                print(f"\n[OK] {len(lines)} Zeilen aus CSV geladen und gesendet\n")
        except Exception as e:
            print(f"[ERROR] Fehler beim Laden der CSV: {e}\n")
    
    print("[WAIT] Warte auf ESP32-Verbindungen...\n")
    
    try:
        while True:
            conn, addr = server_socket.accept()
            # Starte neuen Thread für jede Verbindung
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
    
    except KeyboardInterrupt:
        print("\n\n[STOP] Server gestoppt")
        print(f"\n[STATS] Statistiken:")
        print(f"   Verbindungen: {stats['connections']}")
        print(f"   Empfangen:    {stats['lines_received']} Zeilen")
        print(f"   Gesendet:     {stats['lines_sent']} Zeilen")
        print(f"   Fehler:       {stats['errors']}")
    
    finally:
        server_socket.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    try:
        print("[INIT] Starte ESP32 Gateway...")
        start_tcp_server()
    except Exception as e:
        print(f"[ERROR] FEHLER: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
