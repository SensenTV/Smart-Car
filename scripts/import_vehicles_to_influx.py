import json
import requests
import time

# Konfiguration
VEHICLES_JSON = "config/vehicles.json"
INFLUX_URL = "http://localhost:8086/api/v2/write?org=vehicle_org&bucket=vehicle_data&precision=s"
INFLUX_TOKEN = "vehicle-admin-token"  # ggf. anpassen

# Hilfsfunktion: InfluxDB Line Protocol für vehicle_info

def vehicle_to_line(vehicle):
    tags = [
        f'vehicle_id={vehicle["vehicle_id"]}'
    ]
    fields = []
    for key in ["display_name", "manufacturer", "model", "year", "license_plate", "vin", "fuel_capacity_l", "fuel_type", "color", "notes"]:
        if key in vehicle:
            val = vehicle[key]
            # year und fuel_capacity_l als Integer mit i für InfluxDB
            if key in ("year", "fuel_capacity_l"):
                try:
                    ival = int(val)
                    fields.append(f'{key}={ival}i')
                except Exception:
                    fields.append(f'{key}={val}')
            elif isinstance(val, str):
                val = val.replace('"', "'")
                fields.append(f'{key}="{val}"')
            else:
                fields.append(f'{key}={val}')
    ts = int(time.time())
    return f'vehicle_info,{"".join(tags)} {",".join(fields)} {ts}'

# Lade Fahrzeuge

with open(VEHICLES_JSON, encoding="utf-8") as f:
    data = json.load(f)
    vehicles = data["vehicles"]

# Schreibe alle Fahrzeuge in InfluxDB
lines = []
for v in vehicles:
    lines.append(vehicle_to_line(v))

payload = "\n".join(lines)

headers = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "text/plain; charset=utf-8"
}

response = requests.post(INFLUX_URL, data=payload.encode("utf-8"), headers=headers)

if response.status_code == 204:
    print("Alle Fahrzeuge erfolgreich in InfluxDB geschrieben.")
else:
    print(f"Fehler beim Schreiben: {response.status_code} {response.text}")
