# 📡 LoRaWAN Setup für Smart-Car

Diese Anleitung erklärt, wie du den ESP32 mit dem Uni-Gateway (TTN) verbindest.

---

## 📋 Übersicht

```
┌─────────────────┐     LoRa 868MHz      ┌──────────────┐
│  ESP32 im Auto  │ ──────────────────►  │ Uni-Gateway  │
│  (LoRa Sender)  │                      │   (TTN)      │
└─────────────────┘                      └──────┬───────┘
                                                │
                                                │ Internet
                                                ▼
                                         ┌──────────────┐
                                         │  TTN Cloud   │
                                         └──────┬───────┘
                                                │ Webhook
                                                ▼
┌─────────────────┐     InfluxDB         ┌──────────────┐
│     Grafana     │ ◄─────────────────── │   Node-RED   │
│   Dashboard     │                      │              │
└─────────────────┘                      └──────────────┘
```

---

## 🛠️ Benötigte Hardware

| Komponente | Beschreibung | Ca. Preis |
|------------|--------------|-----------|
| ESP32 LoRa Board | Heltec WiFi LoRa 32 V2 oder TTGO LoRa32 | 15-25€ |
| Antenne | 868 MHz Antenne (meist dabei) | - |
| MPU6050 | Beschleunigungssensor (optional) | 3€ |
| GPS Modul | NEO-6M (optional) | 8€ |
| OLED Display | 0.96" I2C (oft auf Board integriert) | - |

---

## 📁 Dateien auf dem ESP32

Kopiere diese Dateien auf den ESP32:

```
esp32/
├── config.py          # <- config_lorawan.py umbenennen
├── sx127x.py          # LoRa Treiber
├── main.py            # <- main_lorawan.py umbenennen
└── ssd1306.py         # OLED Treiber (optional)
```

---

## 1️⃣ TTN Account & Application erstellen

### 1.1 Account erstellen

1. Gehe zu **https://console.cloud.thethings.network/**
2. Wähle **Europe 1** (eu1.cloud.thethings.network)
3. Erstelle einen Account oder logge dich ein

### 1.2 Application erstellen

1. Klicke auf **"+ Create application"**
2. Fülle aus:
   - **Application ID**: `smartcar` (kleinbuchstaben, keine Leerzeichen)
   - **Application name**: `Smart-Car Tracking`
   - **Description**: `Fahrzeugtelemetrie über LoRaWAN`
3. Klicke **"Create application"**

---

## 2️⃣ End Device registrieren

### 2.1 Device hinzufügen

1. In deiner Application: **"+ Register end device"**
2. Wähle **"Enter end device specifics manually"**

### 2.2 Device Einstellungen

```
Frequency plan:        Europe 863-870 MHz (SF9 for RX2)
LoRaWAN version:       LoRaWAN Specification 1.0.3
Regional Parameters:   RP001 Regional Parameters 1.0.3 revision A
```

### 2.3 Provisioning Information

Wähle **OTAA** (Over-The-Air-Activation):

```
JoinEUI / AppEUI:      0000000000000000  (oder eigene generieren)
DevEUI:                [Generate] klicken
AppKey:                [Generate] klicken
End device ID:         fiesta01  (eindeutig pro Fahrzeug)
```

### 2.4 Keys kopieren

Nach dem Erstellen siehst du die Keys. Kopiere sie in `config_lorawan.py`:

```python
# In TTN Console bei "DevEUI" auf das Auge-Symbol klicken
# Format: MSB (Most Significant Byte first)
DEV_EUI = '70B3D57ED00754DB'

# JoinEUI (früher AppEUI)
JOIN_EUI = '0000000000000000'

# AppKey - WICHTIG: MSB Format!
# Klicke auf "<>" um zwischen MSB/LSB zu wechseln
APP_KEY = '63E84F820D9F1C5C03746C31C285F651'
```

⚠️ **WICHTIG**: Die Keys müssen im **MSB-Format** sein!

---

## 3️⃣ Payload Decoder einrichten

Der Decoder wandelt die binären Daten in lesbare JSON-Werte um.

### 3.1 Decoder hinzufügen

1. In TTN Console: **Applications → smartcar → Payload formatters → Uplink**
2. Formatter type: **Custom Javascript formatter**
3. Füge diesen Code ein:

```javascript
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
        if (value > 32767) value -= 65536;
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
        
        if (lat > 8388607) lat -= 16777216;
        if (lon > 8388607) lon -= 16777216;
        if (alt > 8388607) alt -= 16777216;
        
        data.latitude = lat / 10000;
        data.longitude = lon / 10000;
        data.altitude = alt / 100;
        break;
        
      default:
        i++;
        break;
    }
  }
  
  data.vehicle_id = "FIESTA01";
  
  return {
    data: data,
    warnings: [],
    errors: []
  };
}
```

4. Klicke **"Save changes"**

---

## 4️⃣ Webhook zu Node-RED einrichten

### 4.1 Webhook erstellen

1. In TTN Console: **Applications → smartcar → Integrations → Webhooks**
2. Klicke **"+ Add webhook"**
3. Wähle **Custom webhook**

### 4.2 Webhook Einstellungen

```
Webhook ID:         smartcar-nodered
Webhook format:     JSON
Base URL:           http://DEINE-SERVER-IP:1880/ttn-webhook

Enabled messages:
  ✓ Uplink message
  □ Uplink normalized
  □ Join accept
  □ Downlink ack
  □ Downlink nack
  □ Downlink sent
  □ Downlink failed
  □ Downlink queued
  □ Location solved
  □ Service data
```

⚠️ **Ersetze `DEINE-SERVER-IP`** mit der öffentlichen IP deines Servers!

### 4.3 Port-Forwarding

Falls dein Server hinter einem Router ist:
- Leite Port **1880** (Node-RED) von außen nach innen weiter
- Oder nutze einen Reverse Proxy (nginx)
- Oder nutze ngrok für Tests: `ngrok http 1880`

---

## 5️⃣ Node-RED Flow für TTN

### 5.1 Flow importieren

1. Öffne Node-RED: **http://localhost:1880**
2. Menü → Import → Clipboard
3. Füge diesen Flow ein:

```json
[
    {
        "id": "ttn_webhook",
        "type": "http in",
        "z": "flow_main",
        "name": "TTN Webhook",
        "url": "/ttn-webhook",
        "method": "post",
        "upload": false,
        "swaggerDoc": "",
        "x": 140,
        "y": 400,
        "wires": [["ttn_response", "ttn_parse"]]
    },
    {
        "id": "ttn_response",
        "type": "http response",
        "z": "flow_main",
        "name": "200 OK",
        "statusCode": "200",
        "x": 330,
        "y": 460,
        "wires": []
    },
    {
        "id": "ttn_parse",
        "type": "function",
        "z": "flow_main",
        "name": "TTN → InfluxDB",
        "func": "// TTN Webhook Payload parsen\nlet ttn = msg.payload;\n\n// Sicherheitsprüfung\nif (!ttn.uplink_message || !ttn.uplink_message.decoded_payload) {\n    node.warn('Ungültiges TTN Payload');\n    return null;\n}\n\nlet data = ttn.uplink_message.decoded_payload;\nlet meta = ttn.uplink_message.rx_metadata[0] || {};\nlet device_id = ttn.end_device_ids.device_id || 'unknown';\n\n// Fahrzeug-ID aus Device-ID ableiten\nlet vehicle_id = data.vehicle_id || device_id.toUpperCase();\n\n// Timestamp\nlet ts = Date.now() * 1000000; // Nanosekunden\n\n// InfluxDB Line Protocol erstellen\nlet lines = [];\n\n// Vehicle State\nif (data.fuel_l !== undefined || data.battery_v !== undefined) {\n    let state_line = `vehicle_state,vehicle_id=${vehicle_id},source=lorawan `;\n    let fields = [];\n    \n    if (data.fuel_l !== undefined) fields.push(`fuel_l=${data.fuel_l}`);\n    if (data.battery_v !== undefined) fields.push(`battery_v=${data.battery_v}`);\n    if (data.state) fields.push(`state=\"${data.state}\"`);\n    if (meta.rssi) fields.push(`rssi=${meta.rssi}i`);\n    if (meta.snr) fields.push(`snr=${meta.snr}`);\n    \n    state_line += fields.join(',') + ` ${ts}`;\n    lines.push(state_line);\n}\n\n// GPS\nif (data.latitude !== undefined && data.longitude !== undefined) {\n    let gps_line = `vehicle_gps,vehicle_id=${vehicle_id} ` +\n        `latitude=${data.latitude},longitude=${data.longitude}` +\n        (data.altitude ? `,altitude=${data.altitude}` : '') +\n        ` ${ts}`;\n    lines.push(gps_line);\n}\n\n// IMU/Accelerometer\nif (data.acc_x !== undefined) {\n    let imu_line = `vehicle_imu,vehicle_id=${vehicle_id} ` +\n        `acc_x=${data.acc_x},acc_y=${data.acc_y},acc_z=${data.acc_z} ${ts}`;\n    lines.push(imu_line);\n}\n\n// LoRa Metadaten speichern\nlet lora_line = `lora_stats,vehicle_id=${vehicle_id},gateway_id=${meta.gateway_ids?.gateway_id || 'unknown'} ` +\n    `rssi=${meta.rssi || 0}i,snr=${meta.snr || 0},` +\n    `spreading_factor=${ttn.uplink_message.settings?.spreading_factor || 0}i ` +\n    `${ts}`;\nlines.push(lora_line);\n\n// Ausgabe\nmsg.payload = lines.join('\\n');\nmsg.headers = {\n    'Authorization': 'Token vehicle-admin-token',\n    'Content-Type': 'text/plain; charset=utf-8'\n};\n\nnode.status({fill:'green', shape:'dot', text: `${vehicle_id} @ ${new Date().toLocaleTimeString()}`});\n\nreturn msg;",
        "outputs": 1,
        "x": 340,
        "y": 400,
        "wires": [["influx_ttn", "debug_ttn"]]
    },
    {
        "id": "influx_ttn",
        "type": "http request",
        "z": "flow_main",
        "name": "InfluxDB Write",
        "method": "POST",
        "ret": "txt",
        "paytoqs": "ignore",
        "url": "http://influxdb:8086/api/v2/write?org=vehicle_org&bucket=vehicle_data&precision=ns",
        "x": 560,
        "y": 400,
        "wires": [[]]
    },
    {
        "id": "debug_ttn",
        "type": "debug",
        "z": "flow_main",
        "name": "TTN Debug",
        "active": true,
        "tosidebar": true,
        "console": false,
        "complete": "payload",
        "x": 550,
        "y": 460,
        "wires": []
    }
]
```

4. Klicke **"Import"** und dann **"Deploy"**

---

## 6️⃣ ESP32 flashen

### 6.1 MicroPython installieren

Falls noch nicht geschehen:

```bash
# esptool installieren
pip install esptool

# Flash löschen
esptool.py --port COM3 erase_flash

# MicroPython flashen (Download von micropython.org)
esptool.py --port COM3 --baud 460800 write_flash -z 0x1000 esp32-20231005-v1.21.0.bin
```

### 6.2 Dateien übertragen

```bash
# ampy installieren
pip install adafruit-ampy

# Konfiguration (Keys anpassen!)
ampy -p COM3 put esp32/lora_sender/config_lorawan.py config.py

# LoRa Treiber
ampy -p COM3 put esp32/lora_sender/sx127x.py

# Hauptprogramm
ampy -p COM3 put esp32/lora_sender/main_lorawan.py main.py

# Optional: OLED Treiber
ampy -p COM3 put esp32/lora_sender/ssd1306.py
```

### 6.3 Alternativ: Thonny IDE

1. Öffne **Thonny** (https://thonny.org)
2. Interpreter: **MicroPython (ESP32)**
3. Port: **COM3** (oder entsprechend)
4. Dateien per Drag & Drop auf den ESP32 ziehen

---

## 7️⃣ Testen

### 7.1 ESP32 Monitor

```bash
# Serielle Konsole öffnen
# Windows:
putty -serial COM3 -sercfg 115200

# Linux/Mac:
screen /dev/ttyUSB0 115200
```

Du solltest sehen:
```
========================================
Smart-Car LoRaWAN Sender
Fahrzeug: FIESTA01
DevEUI: 70B3D57ED00754DB
========================================
SX127x OK (Version: 0x12)
LoRa bereit auf 868.1 MHz

Starte LoRaWAN Sender...
[TX] Fuel=35.2L Bat=12.81V State=1
     GPS=(49.2354, 7.0001)
     Payload: 010203... (23 bytes)
     OK! (Total: 1)
```

### 7.2 TTN Console prüfen

1. Gehe zu **Applications → smartcar → Live data**
2. Du solltest Uplink-Nachrichten sehen
3. Klicke auf eine Nachricht um die dekodierten Daten zu sehen

### 7.3 Node-RED prüfen

1. Öffne Node-RED: **http://localhost:1880**
2. Prüfe die Debug-Ausgabe im rechten Panel
3. Du solltest das InfluxDB Line Protocol sehen

### 7.4 Grafana prüfen

1. Öffne Grafana: **http://localhost:3001**
2. Die Daten sollten im Dashboard erscheinen

---

## 🔧 Troubleshooting

### ESP32 sendet nicht

| Problem | Lösung |
|---------|--------|
| `LoRa nicht gefunden` | Pins in `config.py` prüfen |
| `SX127x Version: 0x00` | SPI-Verbindung prüfen |
| Keine LED-Aktivität | Antenne angeschlossen? |

### TTN empfängt nicht

| Problem | Lösung |
|---------|--------|
| Keine Uplinks | Gateway in Reichweite? |
| `MIC failed` | AppKey falsch (MSB/LSB?) |
| `DevNonce reused` | Device in TTN löschen & neu erstellen |

### Webhook funktioniert nicht

| Problem | Lösung |
|---------|--------|
| 404 Error | URL in Node-RED prüfen |
| Connection refused | Port-Forwarding prüfen |
| Timeout | Server erreichbar? Firewall? |

---

## 📊 Fair Use Policy

TTN hat Nutzungslimits für kostenlose Nutzung:

| Limit | Wert |
|-------|------|
| Airtime pro Tag | max. 30 Sekunden |
| Downlinks pro Tag | max. 10 |
| Payload-Größe | max. 51 Bytes (SF12) bis 222 Bytes (SF7) |

### Empfohlene Sendeintervalle

| Spreading Factor | Airtime/Nachricht | Max. Nachrichten/Tag |
|------------------|-------------------|---------------------|
| SF7 | ~50ms | ~600 |
| SF9 | ~200ms | ~150 |
| SF12 | ~1.5s | ~20 |

**Empfehlung**: SF7 mit 60s Intervall = 1440 Nachrichten/Tag = 72s Airtime ⚠️

Für Einhaltung der Fair Use Policy: **Intervall auf 2-5 Minuten erhöhen!**

---

## 🔐 Sicherheit

- **Niemals** AppKey öffentlich teilen
- Keys in TTN Console **regenerieren** wenn kompromittiert
- Webhook mit HTTPS absichern
- Node-RED mit Passwort schützen

---

## 📚 Weiterführende Links

- [TTN Dokumentation](https://www.thethingsnetwork.org/docs/)
- [LoRaWAN Spezifikation](https://lora-alliance.org/resource-hub/)
- [Cayenne LPP Format](https://developers.mydevices.com/cayenne/docs/lora/)
- [Heltec ESP32 LoRa](https://heltec.org/project/wifi-lora-32/)
- [MicroPython ESP32](https://docs.micropython.org/en/latest/esp32/quickref.html)
