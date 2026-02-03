import paho.mqtt.client as mqtt
import json
import base64
import struct
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ---------------------------------------------------------------------------
# 1. KONFIGURATION (BITTE AUSFÜLLEN!)
# ---------------------------------------------------------------------------

# --- TTN EINSTELLUNGEN ---
TTN_APP_ID = "esp32-car-project"  # Deine Application ID
TTN_API_KEY = "NNSXS.LYJRUADYVHYC6SQOB3X4IJS4B5FZYBNC6SB6JII.PFVUPT7ENND3SO4UZ5PBDXQYF3N4QQDFC7CMFNEF6OKYHBGYPDZA" # Der Key mit "Read Traffic" Rechten
TTN_BROKER = "eu1.cloud.thethings.network"

# --- INFLUXDB EINSTELLUNGEN (Lokal) ---
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "vehicle-admin-token" # Endet oft auf "=="
INFLUX_ORG = "vehicle_org"     # Name deiner Organisation
INFLUX_BUCKET = "vehicle_data"   # Name deines Buckets

# ---------------------------------------------------------------------------
# 2. INFLUXDB VERBINDUNG
# ---------------------------------------------------------------------------

def connect_influx():
    """Stellt Verbindung zur Datenbank her"""
    print(f"Verbinde zu InfluxDB unter {INFLUX_URL}...")
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        # Kurzer Check ob DB antwortet
        health = client.health()
        if health.status == "pass":
            print("✅ InfluxDB Verbindung erfolgreich!")
            return client
        else:
            print("❌ InfluxDB antwortet, aber Status ist nicht 'pass'.")
            return None
    except Exception as e:
        print(f"❌ Kritischer Fehler bei InfluxDB Verbindung: {e}")
        return None

def write_to_influx(db_client, vehicle_id, fuel, voltage, tires):
    """Erstellt einen Datenpunkt und sendet ihn an InfluxDB"""
    if db_client is None: return

    write_api = db_client.write_api(write_options=SYNCHRONOUS)
    
    # Datenpunkt definieren
    # Measurement: "vehicle_status"
    # Tag: ID (um nach Autos zu filtern)
    # Fields: Die echten Messwerte
    p = Point("vehicle_status") \
        .tag("vehicle_id", f"CAR_{vehicle_id:03d}") \
        .field("fuel_level", int(fuel)) \
        .field("voltage", float(voltage)) \
        .field("tire_vl", float(tires[0])) \
        .field("tire_vr", float(tires[1])) \
        .field("tire_hl", float(tires[2])) \
        .field("tire_hr", float(tires[3]))
        
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        print("💾 Daten erfolgreich in InfluxDB gespeichert.")
    except Exception as e:
        print(f"⚠️ Fehler beim Schreiben in die DB: {e}")

# ---------------------------------------------------------------------------
# 3. MQTT LOGIK (DATEN EMPFANGEN)
# ---------------------------------------------------------------------------

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Verbunden mit TTN MQTT Broker!")
        # Wir abonnieren den Uplink-Traffic
        topic = f"v3/{TTN_APP_ID}@ttn/devices/+/up"
        client.subscribe(topic)
        print(f"📡 Lausche auf Topic: {topic}")
    else:
        print(f"❌ MQTT Verbindung fehlgeschlagen, Code: {rc}")

def on_message(client, userdata, msg):
    print("\n📩 Neue Nachricht empfangen!")
    db_client = userdata['db_client'] # DB Client aus Userdata holen
    
    try:
        # 1. JSON parsen
        message_json = json.loads(msg.payload.decode('utf-8'))
        
        # 2. Base64 Payload finden und decodieren
        raw_payload = message_json['uplink_message']['frm_payload']
        payload_bytes = base64.b64decode(raw_payload)
        
        # 3. Bytes entpacken (Gegenstück zum Arduino Code)
        # Wir erwarten 7 Bytes: ID(1), Fuel(1), Volt(1), 4xReifen(1)
        if len(payload_bytes) == 7:
            data = struct.unpack('BBBBBBB', payload_bytes)
            
            # Werte zuordnen
            v_id = data[0]
            fuel = data[1]
            
            # Werte zurückrechnen (durch 10 teilen)
            voltage = data[2] / 10.0
            
            tire_vl = data[3] / 10.0
            tire_vr = data[4] / 10.0
            tire_hl = data[5] / 10.0
            tire_hr = data[6] / 10.0
            
            tires = [tire_vl, tire_vr, tire_hl, tire_hr]

            print(f"🚗 Auto ID: {v_id} | Tank: {fuel}% | Spg: {voltage}V | Reifen: {tires}")
            
            # 4. Ab in die Datenbank damit
            write_to_influx(db_client, v_id, fuel, voltage, tires)
            
        else:
            print(f"⚠️ Payload hat falsche Länge: {len(payload_bytes)} Bytes (Erwarte 7)")

    except Exception as e:
        print(f"❌ Fehler bei der Verarbeitung: {e}")

# ---------------------------------------------------------------------------
# 4. HAUPTPROGRAMM
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("--- START TTN ZU INFLUXDB BRIDGE ---")
    
    # 1. InfluxDB verbinden
    db_client = connect_influx()
    if db_client is None:
        print("Abbruch: Keine Datenbankverbindung.")
        exit(1)

    # 2. MQTT Client einrichten
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(f"{TTN_APP_ID}@ttn", TTN_API_KEY)
    
    # Callbacks setzen
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    # Den DB-Client an die Callbacks "vererben"
    mqtt_client.user_data_set({'db_client': db_client})

    try:
        # 3. Verbinden und warten
        mqtt_client.connect(TTN_BROKER, 1883, 60)
        print("Warte auf Daten... (STRG+C zum Beenden)")
        mqtt_client.loop_forever()
        
    except KeyboardInterrupt:
        print("\nProgramm beendet.")
        mqtt_client.disconnect()
        db_client.close()