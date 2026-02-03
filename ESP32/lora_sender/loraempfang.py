import paho.mqtt.client as mqtt
import json
import base64
import random
import struct
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- KONFIGURATION ---
TTN_APP_ID = "esp32-car-project"
TTN_API_KEY = "NNSXS.LYJRUADYVHYC6SQOB3X4IJS4B5FZYBNC6SB6JII.PFVUPT7ENND3SO4UZ5PBDXQYF3N4QQDFC7CMFNEF6OKYHBGYPDZA" 
TTN_BROKER = "eu1.cloud.thethings.network"

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "vehicle-admin-token" 
INFLUX_ORG = "vehicle_org"
INFLUX_BUCKET = "vehicle_data"

# ---------------------------------------------------------------------------
# MAPPINGS
# ---------------------------------------------------------------------------
VEHICLE_NAMES = {
    1: "Ford_Siesta",
}

ERROR_CODES = {
    1: "BATTERY_LOW",
    2: "CHECK_ENGINE",
    3: "LOW_OIL",
    4: "TIRE_PRESSURE",
}

# Message Types
MSG_STATUS = 1      # Normaler Fahrstatus
MSG_TRIP_END = 2    # Fahrt beendet (Trip Summary)
MSG_ERROR = 3       # Fehler melden
MSG_IDLE = 4        # Fahrzeug steht (idle)

# ---------------------------------------------------------------------------
# DATENBANK SCHREIBEN
# ---------------------------------------------------------------------------
def write_to_influx(db_client, v_id, msg_type, values):
    """
    Minimale Payload Formate (4 Bytes):
    - Status (1):   [ID, Type, Fuel, Battery*10]
    - Trip End (2): [ID, Type, Duration_min, FuelUsed*10]
    - Error (3):    [ID, Type, ErrorCode, Battery*10]
    - Idle (4):     [ID, Type, Fuel, Battery*10]
    """
    write_api = db_client.write_api(write_options=SYNCHRONOUS)
    
    v_name = VEHICLE_NAMES.get(v_id, f"Car_{v_id}")
    points = []

    # --- TYP 1: STATUS (Driving) ---
    if msg_type == MSG_STATUS:
        fuel = values[0]
        battery = values[1] / 10.0
        
        p = Point("vehicle_state") \
            .tag("vehicle_id", v_name) \
            .field("fuel_l", float(fuel)) \
            .field("battery_v", float(battery)) \
            .field("state", "driving")
        points.append(p)

    # --- TYP 2: TRIP SUMMARY (Fahrt Ende) ---
    elif msg_type == MSG_TRIP_END:
        duration_min = values[0]
        fuel_used = values[1] / 10.0
        
        trip_id = f"TRIP_{v_name}_{random.randint(1000, 9999)}"
        
        p = Point("trip_summary") \
            .tag("vehicle_id", v_name) \
            .tag("trip_id", trip_id) \
            .field("duration_s", float(duration_min * 60)) \
            .field("fuel_used", float(fuel_used))
        points.append(p)
        
        # Status auf "parked" setzen
        p_state = Point("vehicle_state") \
            .tag("vehicle_id", v_name) \
            .field("state", "parked")
        points.append(p_state)
        
        print(f"[OK] {v_name} TRIP ENDE | Dauer: {duration_min}min | Verbrauch: {fuel_used}L")

    # --- TYP 3: ERROR (Fehler) ---
    elif msg_type == MSG_ERROR:
        error_id = values[0]
        battery = values[1] / 10.0
        
        error_msg = ERROR_CODES.get(error_id, f"ERROR_{error_id}")
        
        p_err = Point("vehicle_errors") \
            .tag("vehicle_id", v_name) \
            .tag("error_code", error_msg) \
            .field("active", 1)
        points.append(p_err)
        
        p_state = Point("vehicle_state") \
            .tag("vehicle_id", v_name) \
            .field("battery_v", float(battery)) \
            .field("state", "error")
        points.append(p_state)
        
        print(f"[ERR] {v_name} FEHLER: {error_msg} | Batt: {battery}V")

    # --- TYP 4: IDLE (Steht) ---
    elif msg_type == MSG_IDLE:
        fuel = values[0]
        battery = values[1] / 10.0
        
        p = Point("vehicle_state") \
            .tag("vehicle_id", v_name) \
            .field("fuel_l", float(fuel)) \
            .field("battery_v", float(battery)) \
            .field("state", "idle")
        points.append(p)
        
        print(f"[OK] {v_name} IDLE | Tank: {fuel}L | Batt: {battery}V")

    # --- UNBEKANNTER TYP ---
    else:
        print(f"? {v_name} Unbekannter Typ: {msg_type}")
        return

    # Immer: Vehicle Info für Dropdown
    p_info = Point("vehicle_info") \
        .tag("vehicle_id", v_name) \
        .field("display_name", v_name)
    points.append(p_info)

    # Schreiben
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    except Exception as e:
        print(f"DB Fehler: {e}")

# ---------------------------------------------------------------------------
# MQTT CALLBACKS
# ---------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[OK] Verbunden mit TTN!")
        client.subscribe(f"v3/{TTN_APP_ID}@ttn/devices/+/up")
    else:
        print(f"Verbindung fehlgeschlagen: {rc}")

def on_message(client, userdata, msg):
    try:
        data_json = json.loads(msg.payload.decode('utf-8'))
        raw_payload = data_json['uplink_message']['frm_payload']
        payload_bytes = base64.b64decode(raw_payload)
        
        device_id = data_json.get('end_device_ids', {}).get('device_id', 'unknown')
        
        # Minimum 4 Bytes: ID, Type, Val1, Val2
        if len(payload_bytes) >= 4:
            v_id = payload_bytes[0]
            msg_type = payload_bytes[1]
            values = list(payload_bytes[2:])
            
            print(f"\n--- {device_id} | {len(payload_bytes)} Bytes ---")
            write_to_influx(userdata['db'], v_id, msg_type, values)
        else:
            print(f"[WARN] Payload zu kurz: {len(payload_bytes)} Bytes (min. 4)")
            
    except KeyError as e:
        print(f"Fehlender Key: {e}")
    except Exception as e:
        print(f"Fehler: {e}")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("  LoRa Bridge für Smart-Car Dashboard")
    print("  Unterstützt: Status, Trip, Error, Idle")
    print("=" * 50)
    
    # DB verbinden
    db = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    print(f"InfluxDB: {INFLUX_URL}")
    
    # MQTT Client
    client = mqtt.Client()
    client.username_pw_set(f"{TTN_APP_ID}@ttn", TTN_API_KEY)
    client.on_connect = on_connect
    client.on_message = on_message
    client.user_data_set({'db': db})

    try:
        print(f"→ Verbinde mit TTN ({TTN_BROKER})...")
        client.connect(TTN_BROKER, 1883, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nBeendet.")
    except Exception as e:
        print(f"Verbindungsfehler: {e}")