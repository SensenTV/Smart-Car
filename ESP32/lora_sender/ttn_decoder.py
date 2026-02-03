"""
TTN Payload Decoder für Smart-Car
Kopiere diesen Code in die TTN Console:
Applications -> Deine App -> Payload formatters -> Uplink -> Custom Javascript

Das dekodiert die Cayenne LPP Daten automatisch und 
leitet sie an deinen Webhook weiter.
"""

# ============================================
# JAVASCRIPT CODE FÜR TTN CONSOLE
# ============================================

TTN_DECODER_JS = """
// Smart-Car TTN Payload Decoder
// Dekodiert Cayenne LPP Format

function decodeUplink(input) {
  var data = {};
  var bytes = input.bytes;
  var i = 0;
  
  while (i < bytes.length) {
    var channel = bytes[i++];
    var type = bytes[i++];
    
    switch (type) {
      case 0x00: // Digital Input (State)
        if (channel === 3) {
          var stateCode = bytes[i++];
          data.state_code = stateCode;
          data.state = ["unknown", "parked", "idle", "driving"][stateCode] || "unknown";
        }
        break;
        
      case 0x02: // Analog Input (Fuel, Battery)
        var value = (bytes[i++] << 8) | bytes[i++];
        if (value > 32767) value -= 65536; // Signed
        value = value / 100;
        
        if (channel === 1) {
          data.fuel_l = value;
        } else if (channel === 2) {
          data.battery_v = value;
        }
        break;
        
      case 0x71: // Accelerometer (IMU)
        var ax = (bytes[i++] << 8) | bytes[i++];
        var ay = (bytes[i++] << 8) | bytes[i++];
        var az = (bytes[i++] << 8) | bytes[i++];
        
        if (ax > 32767) ax -= 65536;
        if (ay > 32767) ay -= 65536;
        if (az > 32767) az -= 65536;
        
        data.acc_x = ax / 1000;
        data.acc_y = ay / 1000;
        data.acc_z = az / 1000;
        break;
        
      case 0x88: // GPS
        var lat = (bytes[i++] << 16) | (bytes[i++] << 8) | bytes[i++];
        var lon = (bytes[i++] << 16) | (bytes[i++] << 8) | bytes[i++];
        var alt = (bytes[i++] << 16) | (bytes[i++] << 8) | bytes[i++];
        
        // Sign extension für 24-bit
        if (lat > 8388607) lat -= 16777216;
        if (lon > 8388607) lon -= 16777216;
        if (alt > 8388607) alt -= 16777216;
        
        data.latitude = lat / 10000;
        data.longitude = lon / 10000;
        data.altitude = alt / 100;
        break;
        
      default:
        // Unbekannter Typ, überspringe
        i++;
        break;
    }
  }
  
  // Metadaten hinzufügen
  data.vehicle_id = input.fPort === 1 ? "FIESTA01" : "UNKNOWN";
  
  return {
    data: data,
    warnings: [],
    errors: []
  };
}
"""

# ============================================
# ALTERNATIVE: Webhook direkt an Node-RED
# ============================================

TTN_WEBHOOK_SETUP = """
TTN Webhook Einrichtung:
========================

1. TTN Console öffnen: https://console.cloud.thethings.network/

2. Applications -> Deine App -> Integrations -> Webhooks

3. "+ Add webhook" klicken

4. Einstellungen:
   - Webhook ID: smartcar-nodered
   - Webhook format: JSON
   - Base URL: http://DEINE-SERVER-IP:1880/ttn-webhook
   - Enabled messages: ✓ Uplink message

5. In Node-RED einen HTTP-In Node erstellen:
   - Method: POST
   - URL: /ttn-webhook
"""

# ============================================
# Node-RED Flow für TTN Webhook
# ============================================

NODERED_TTN_FLOW = """
Füge diesen Flow in Node-RED ein (Import -> Clipboard):

[
    {
        "id": "ttn_webhook_in",
        "type": "http in",
        "name": "TTN Webhook",
        "url": "/ttn-webhook",
        "method": "post",
        "x": 150,
        "y": 100,
        "wires": [["ttn_parse"]]
    },
    {
        "id": "ttn_parse",
        "type": "function",
        "name": "TTN Parser",
        "func": "// TTN Payload extrahieren\\nlet ttn = msg.payload;\\nlet data = ttn.uplink_message.decoded_payload;\\nlet meta = ttn.uplink_message.rx_metadata[0];\\n\\n// Für InfluxDB formatieren\\nlet vehicle_id = data.vehicle_id || 'UNKNOWN';\\nlet ts = Date.now() * 1000000;\\n\\n// State Line\\nlet state_line = `vehicle_state,vehicle_id=${vehicle_id} ` +\\n    `fuel_l=${data.fuel_l || 0},` +\\n    `battery_v=${data.battery_v || 0},` +\\n    `state=\\"${data.state || 'unknown'}\\",` +\\n    `rssi=${meta.rssi || 0}i,` +\\n    `snr=${meta.snr || 0} ${ts}`;\\n\\nmsg.payload = state_line;\\nmsg.headers = {\\n    'Authorization': 'Token vehicle-admin-token',\\n    'Content-Type': 'text/plain'\\n};\\n\\nreturn msg;",
        "x": 350,
        "y": 100,
        "wires": [["influx_write"]]
    },
    {
        "id": "influx_write",
        "type": "http request",
        "name": "InfluxDB",
        "method": "POST",
        "url": "http://influxdb:8086/api/v2/write?org=vehicle_org&bucket=vehicle_data&precision=ns",
        "x": 550,
        "y": 100,
        "wires": [[]]
    }
]
"""

if __name__ == "__main__":
    print("=" * 50)
    print("TTN DECODER JAVASCRIPT")
    print("=" * 50)
    print(TTN_DECODER_JS)
    print("\n")
    print("=" * 50)
    print("WEBHOOK SETUP")
    print("=" * 50)
    print(TTN_WEBHOOK_SETUP)
