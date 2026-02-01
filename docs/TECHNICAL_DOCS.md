# Technische Dokumentation - Smart-Car IoT Platform

> Umfassende technische Dokumentation fuer Entwickler und Administratoren

---

## Inhaltsverzeichnis

1. [Systemuebersicht](#1-systemuebersicht)
2. [Komponenten im Detail](#2-komponenten-im-detail)
3. [Datenfluss](#3-datenfluss)
4. [MQTT-Protokoll](#4-mqtt-protokoll)
5. [Datenmodell (InfluxDB)](#5-datenmodell-influxdb)
6. [Node-RED Flows](#6-node-red-flows)
7. [Grafana Dashboards](#7-grafana-dashboards)
8. [ESP32 Integration](#8-esp32-integration)
9. [Sicherheit](#9-sicherheit)
10. [Troubleshooting](#10-troubleshooting)
11. [API-Referenz](#11-api-referenz)

---

## 1. Systemuebersicht

### 1.1 Architekturprinzipien

Das Smart-Car System folgt einer **ereignisgesteuerten Microservice-Architektur**:

- **Lose Kopplung**: Komponenten kommunizieren ueber MQTT
- **Skalierbarkeit**: Jeder Service laeuft in eigenem Container
- **Ausfallsicherheit**: Message Queue puffert bei Ausfaellen
- **Erweiterbarkeit**: Neue Datenquellen einfach integrierbar

### 1.2 Technologie-Stack

| Schicht | Technologie | Version | Zweck |
|---------|-------------|---------|-------|
| **Hardware** | ESP32 | - | Datenerfassung |
| **Transport** | MQTT (Mosquitto) | 2.x | Nachrichtenuebertragung |
| **Verarbeitung** | Node-RED | 3.x | ETL und Alarmierung |
| **Speicherung** | InfluxDB | 2.x | Zeitreihendatenbank |
| **Visualisierung** | Grafana | 10.x+ | Dashboards |
| **Orchestrierung** | Docker Compose | 3.8 | Container-Management |

### 1.3 Netzwerk-Topologie

```
+-------------------------------------------------------------+
|                    Docker Network                           |
|                  (smartcar-network)                         |
|                                                             |
|  +-----------+   +-----------+   +-----------+             |
|  | mosquitto |   |  node-red |   | influxdb  |             |
|  |  :1883    |<--|   :1880   |-->|  :8086    |             |
|  |  :8883    |   +-----------+   +-----+-----+             |
|  +-----+-----+                         |                    |
|        |                               |                    |
|        |                         +-----v-----+             |
|        |                         |  grafana  |             |
|        |                         |  :3001    |             |
|        |                         +-----------+             |
+---------+---------------------------------------------------+
          |
          | Port 8883 (TLS)
          v
   +-----------+
   |   ESP32   |
   |  Devices  |
   +-----------+
```

---

## 2. Komponenten im Detail

### 2.1 Mosquitto MQTT Broker

**Funktion**: Zentrale Nachrichtenvermittlung zwischen ESP32 und Node-RED

**Konfiguration** (`mosquitto/config/mosquitto.conf`):
```properties
# Unverschluesselter Port (nur intern)
listener 1883
protocol mqtt

# TLS-verschluesselter Port (extern)
listener 8883
protocol mqtt
cafile /mosquitto/config/certs/ca.crt
certfile /mosquitto/config/certs/mosquitto.crt
keyfile /mosquitto/config/certs/mosquitto.key
tls_version tlsv1.2

# Anonyme Verbindungen erlaubt
allow_anonymous true
```

**Ports**:
| Port | Protokoll | Verwendung |
|------|-----------|------------|
| 1883 | MQTT | Interne Kommunikation (Node-RED) |
| 8883 | MQTTS | Externe Geraete (ESP32 mit TLS) |

### 2.2 Node-RED

**Funktion**: Datenverarbeitung, Transformation und Alarmierung

**Konfiguration** (`node-red/settings.js`):
- Flow-Speicherort: `/data/flows.json`
- Credentials: `/data/flows_cred.json`

**Flow-Funktionalitaet**:
- CSV-Parsing von MQTT-Nachrichten
- Konvertierung zu InfluxDB Line Protocol
- HTTP-basiertes Schreiben nach InfluxDB

### 2.3 InfluxDB 2.x

**Funktion**: Speicherung und Abfrage von Zeitreihendaten

**Konfiguration**:
| Parameter | Wert |
|-----------|------|
| Organisation | `vehicle_org` |
| Bucket | `vehicle_data` |
| Retention | Standard (unbegrenzt) |
| Admin-Token | `vehicle-admin-token` |

**Wichtige Konzepte**:
- **Bucket**: Container fuer Zeitreihendaten
- **Measurement**: Aequivalent zu SQL-Tabelle
- **Tag**: Indexierte Metadaten (z.B. vehicle_id)
- **Field**: Messwerte (z.B. fuel_l, battery_v)

### 2.4 Grafana

**Funktion**: Visualisierung und Alerting

**Provisioning-Struktur**:
```
grafana/provisioning/
|-- dashboards/
|   |-- dashboards.yml         # Dashboard-Provider
|   |-- main-dashboard.json    # Hauptuebersicht
|   +-- vehicle-detail-dashboard.json
+-- datasources/
    +-- datasources.yml        # Datenquellen
```

---

## 3. Datenfluss

### 3.1 End-to-End Flow

```
ESP32 Sensor  -->  MQTT Publish  -->  Mosquitto  -->  Node-RED Subscribe
                                                           |
                                                           v
                                                     CSV Parsing
                                                           |
                                                           v
                                                     Line Protocol
                                                           |
                                                           v
                                                     HTTP POST
                                                           |
                                                           v
                                                      InfluxDB
                                                           |
                                                           v
                                                       Grafana
```

### 3.2 Latenz-Erwartungen

| Strecke | Erwartete Latenz |
|---------|------------------|
| ESP32 --> Mosquitto | 10-50ms (WLAN) |
| Mosquitto --> Node-RED | < 5ms |
| Node-RED --> InfluxDB | 5-20ms |
| InfluxDB --> Grafana | 50-200ms (Query) |
| **Gesamt** | **< 300ms** |

---

## 4. MQTT-Protokoll

### 4.1 Topic-Struktur

```
smartcar/{vehicle_id}
```

Alle Nachrichtentypen werden auf diesem Topic publiziert.

### 4.2 Nachrichtenformate

#### Fahrzeugstatus (state)
```
state,{vehicle_id},{state_name},{fuel_l},{battery_v}
```

| Feld | Typ | Beschreibung | Beispiel |
|------|-----|--------------|----------|
| vehicle_id | String | Fahrzeug-Kennung | CAR001 |
| state_name | String | Fahrzeugzustand | idle, driving, charging, parked |
| fuel_l | Float | Kraftstoff in Litern | 45.5 |
| battery_v | Float | Batteriespannung | 12.8 |

#### Fahrt-Zusammenfassung (trip)
```
trip,{vehicle_id},{trip_id},{duration_s},{fuel_used},{max_acc},{max_brake}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| trip_id | String | Eindeutige Fahrt-ID |
| duration_s | Integer | Fahrtdauer in Sekunden |
| fuel_used | Float | Verbrauchter Kraftstoff |
| max_acc | Float | Maximale Beschleunigung |
| max_brake | Float | Maximale Bremsung |

#### Fehler (error)
```
error,{vehicle_id},{error_code},{active}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| error_code | String | OBD-II Fehlercode (z.B. P0420) |
| active | Integer | 1 = aktiv, 0 = geloest |

#### GPS-Position (gps)
```
gps,{vehicle_id},{latitude},{longitude},{speed_kmh}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| latitude | Float | Breitengrad |
| longitude | Float | Laengengrad |
| speed_kmh | Float | Geschwindigkeit in km/h |

#### Alarm (alert)
```
alert,{vehicle_id},{alert_type},{message}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| alert_type | String | Alarm-Typ (z.B. fuel_low) |
| message | String | Alarm-Nachricht |

### 4.3 QoS-Level

| Level | Beschreibung | Empfehlung |
|-------|--------------|------------|
| QoS 0 | At most once | Nicht empfohlen |
| QoS 1 | At least once | Standard fuer Telemetrie |
| **QoS 2** | Exactly once | **Empfohlen fuer Fehler** |

---

## 5. Datenmodell (InfluxDB)

### 5.1 Measurements

#### vehicle_state
```
Measurement: vehicle_state
Tags:
  - vehicle_id (String)
  - state (String)
Fields:
  - fuel_l (Float)
  - battery_v (Float)
  - online (Integer)
```

#### trip_summary
```
Measurement: trip_summary
Tags:
  - vehicle_id (String)
  - trip_id (String)
Fields:
  - duration_s (Integer)
  - fuel_used (Float)
  - max_acceleration (Float)
  - max_braking (Float)
```

#### vehicle_errors
```
Measurement: vehicle_errors
Tags:
  - vehicle_id (String)
  - error_code (String)
Fields:
  - active (Integer)
```

#### vehicle_gps
```
Measurement: vehicle_gps
Tags:
  - vehicle_id (String)
Fields:
  - latitude (Float)
  - longitude (Float)
  - speed_kmh (Float)
```

#### alerts
```
Measurement: alerts
Tags:
  - vehicle_id (String)
  - alert_type (String)
Fields:
  - message (String)
```

### 5.2 Beispiel-Queries (Flux)

**Letzte Fahrzeugzustaende:**
```flux
from(bucket: "vehicle_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "vehicle_state")
  |> filter(fn: (r) => r.vehicle_id == "CAR001")
  |> last()
```

**Aktive Fahrzeuge zaehlen:**
```flux
from(bucket: "vehicle_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "vehicle_state")
  |> filter(fn: (r) => r._field == "online")
  |> group(columns: ["vehicle_id"])
  |> last()
  |> group()
  |> count()
```

**Aktive Fehler:**
```flux
from(bucket: "vehicle_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "vehicle_errors")
  |> filter(fn: (r) => r._field == "active")
  |> group(columns: ["vehicle_id", "error_code"])
  |> last()
  |> filter(fn: (r) => r._value == 1)
```

---

## 6. Node-RED Flows

### 6.1 Hauptflow: MQTT --> InfluxDB

```
[MQTT In] --> [Function: CSV zu Line Protocol] --> [HTTP Request] --> [Debug]
```

### 6.2 CSV Parser Logik

```javascript
// CSV -> InfluxDB Line Protocol Transformation
let topicParts = msg.topic.split('/');
let vehicle_id = topicParts[1] || 'UNKNOWN';
let cols = msg.payload.toString().trim().split(',');
let type = cols[0].toLowerCase();
let line = '';
let ts = Date.now() * 1000000; // nanoseconds

switch(type) {
    case 'state':
        let state = cols[2] || 'unknown';
        let fuel = parseFloat(cols[3]) || 0;
        let battery = parseFloat(cols[4]) || 0;
        line = `vehicle_state,vehicle_id=${vehicle_id},state=${state} fuel_l=${fuel},battery_v=${battery},online=1i ${ts}`;
        break;
        
    case 'error':
        let error_code = cols[2];
        let active = parseInt(cols[3]) === 1 ? 1 : 0;
        line = `vehicle_errors,vehicle_id=${vehicle_id},error_code=${error_code} active=${active}i ${ts}`;
        break;
        
    case 'trip':
        let trip_id = cols[2];
        let duration = parseInt(cols[3]) || 0;
        let fuel_used = parseFloat(cols[4]) || 0;
        let max_acc = parseFloat(cols[5]) || 0;
        let max_brake = parseFloat(cols[6]) || 0;
        line = `trip_summary,vehicle_id=${vehicle_id},trip_id=${trip_id} duration_s=${duration}i,fuel_used=${fuel_used},max_acceleration=${max_acc},max_braking=${max_brake} ${ts}`;
        break;
        
    case 'gps':
        let lat = parseFloat(cols[2]) || 0;
        let lon = parseFloat(cols[3]) || 0;
        let speed = parseFloat(cols[4]) || 0;
        line = `vehicle_gps,vehicle_id=${vehicle_id} latitude=${lat},longitude=${lon},speed_kmh=${speed} ${ts}`;
        break;

    case 'alert':
        let alert_type = cols[2];
        let alert_msg = cols[3] || '';
        line = `alerts,vehicle_id=${vehicle_id},alert_type=${alert_type} message="${alert_msg}" ${ts}`;
        break;
}

msg.payload = line;
msg.headers = {
    'Authorization': 'Token vehicle-admin-token',
    'Content-Type': 'text/plain'
};
return msg;
```

### 6.3 HTTP Request Konfiguration

- **URL**: `http://influxdb:8086/api/v2/write?org=vehicle_org&bucket=vehicle_data&precision=ns`
- **Methode**: POST
- **Headers**: Authorization Token

---

## 7. Grafana Dashboards

### 7.1 Hauptdashboard (Flottenuebersicht)

**UID**: `smart-car-main`

**Panels:**
1. **Aktive Fahrzeuge** (Stat)
   - Zeigt Anzahl der aktiven Fahrzeuge

2. **Aktive Fehler** (Stat)
   - Anzahl nicht geloester Fehler

3. **Fahrten 24h** (Stat)
   - Anzahl Fahrten in den letzten 24 Stunden

4. **Alarme 24h** (Stat)
   - Anzahl Alarme in den letzten 24 Stunden

5. **Kraftstoffstand** (Time Series)
   - Verlauf des Kraftstoffstands pro Fahrzeug

6. **Batteriespannung** (Time Series)
   - Verlauf der Batteriespannung pro Fahrzeug

7. **Fahrzeugliste** (Table)
   - Liste aller Fahrzeuge mit aktuellem Status

8. **Fehlerliste** (Table)
   - Liste aller Fehler

9. **Letzte Fahrten** (Table)
   - Liste der letzten Fahrten

10. **Letzte Alarme** (Table)
    - Liste der letzten Alarme

### 7.2 Detail-Dashboard (Fahrzeug Details)

**UID**: `smart-car-detail`

**Variablen:**
- `$vehicle_id` - Ausgewaehltes Fahrzeug (Dropdown)

**Panels:**
1. Status (Stat)
2. Kraftstoff (Gauge)
3. Batterie (Gauge)
4. Fahrten 7 Tage (Stat)
5. Kraftstoffverlauf (Time Series)
6. Batterieverlauf (Time Series)
7. Letzte Fahrten (Table)
8. Fahrzeugfehler (Table)
9. Alarme (Table)

### 7.3 Dashboard-Provisioning

```yaml
# dashboards.yml
apiVersion: 1
providers:
  - name: 'default'
    folder: 'Smart-Car'
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

---

## 8. ESP32 Integration

### 8.1 Hardware-Setup

#### WLAN-Modul (integriert)
- Standardmaessig in ESP32 enthalten
- 802.11 b/g/n, 2.4 GHz

#### LoRa-Modul (extern)
**Empfohlene Module:**
- SX1276 / SX1278
- Frequenz: 868 MHz (EU) / 915 MHz (US)
- Reichweite: bis 10 km (Sichtverbindung)

**Pinbelegung:**
| LoRa Pin | ESP32 Pin |
|----------|-----------|
| VCC | 3.3V |
| GND | GND |
| SCK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| NSS | GPIO 5 |
| RST | GPIO 14 |
| DIO0 | GPIO 26 |

### 8.2 Bibliotheken

```cpp
// platformio.ini
[env:esp32]
platform = espressif32
board = esp32dev
framework = arduino
lib_deps =
    knolleary/PubSubClient@^2.8
    sandeepmistry/LoRa@^0.8.0
    bblanchon/ArduinoJson@^6.21
```

### 8.3 Stromverbrauch-Optimierung

| Modus | Stromverbrauch | Anwendung |
|-------|----------------|-----------|
| Active | ~240 mA | Datenuebertragung |
| Modem Sleep | ~20 mA | WiFi connected, idle |
| Light Sleep | ~0.8 mA | Periodische Messung |
| Deep Sleep | ~10 uA | Langzeit-Standby |

**Deep Sleep Beispiel:**
```cpp
#define uS_TO_S_FACTOR 1000000
#define TIME_TO_SLEEP  60  // 60 Sekunden

void setup() {
    // Messung und Uebertragung
    sendData();
    
    // Deep Sleep
    esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
    esp_deep_sleep_start();
}
```

---

## 9. Sicherheit

### 9.1 TLS-Zertifikate

**Zertifikatsstruktur:**
```
mosquitto/config/certs/
|-- ca.crt          # Certificate Authority
|-- mosquitto.crt   # Server-Zertifikat
+-- mosquitto.key   # Privater Schluessel
```

**Generierung:**
```bash
# Private Key
openssl genrsa -out mosquitto.key 2048

# Zertifikat (10 Jahre gueltig)
openssl req -new -x509 -key mosquitto.key -out mosquitto.crt -days 3650 \
  -subj "/C=DE/ST=Berlin/L=Berlin/O=SmartCar/CN=mosquitto"

# CA = Self-signed
cp mosquitto.crt ca.crt
```

### 9.2 Empfohlene Sicherheitsmassnahmen

| Massnahme | Status | Prioritaet |
|----------|--------|-----------|
| TLS fuer MQTT | Implementiert | Hoch |
| MQTT-Authentifizierung | Optional | Mittel |
| Grafana-Passwort | Konfiguriert | Hoch |
| InfluxDB-Token | Konfiguriert | Hoch |
| Netzwerk-Isolation | Docker Network | Mittel |

### 9.3 MQTT-Authentifizierung (Optional)

```properties
# mosquitto.conf
allow_anonymous false
password_file /mosquitto/config/passwd
```

```bash
# Passwort-Datei erstellen
docker exec -it mosquitto mosquitto_passwd -c /mosquitto/config/passwd esp32user
```

---

## 10. Troubleshooting

### 10.1 Haeufige Probleme

#### Container startet nicht
```bash
# Logs pruefen
docker-compose logs <service>

# Container neu starten
docker-compose restart <service>
```

#### MQTT-Verbindung fehlgeschlagen
```bash
# Mosquitto-Status pruefen
docker exec mosquitto mosquitto_sub -t '$SYS/#' -C 1

# Verbindung testen
docker exec mosquitto mosquitto_pub -t test -m "hello"
```

#### Keine Daten in InfluxDB
1. Node-RED Debug-Panel pruefen
2. InfluxDB-Verbindung in Node-RED testen
3. Bucket-Berechtigung pruefen

#### Grafana zeigt keine Daten
1. Datenquelle testen (Data Sources --> Test)
2. Query im Explore-Modus testen
3. Zeitbereich pruefen

### 10.2 Log-Dateien

| Service | Log-Zugang |
|---------|------------|
| Mosquitto | `docker logs mosquitto` oder `./mosquitto/log/` |
| Node-RED | `docker logs node-red` |
| InfluxDB | `docker logs influxdb` |
| Grafana | `docker logs grafana` |

### 10.3 Nuetzliche Befehle

```bash
# Alle Container neustarten
docker-compose down && docker-compose up -d

# Container-Status
docker-compose ps

# In Container einloggen
docker exec -it <container> sh

# Netzwerk pruefen
docker network inspect smartcar-network

# Ressourcenverbrauch
docker stats
```

---

## 11. API-Referenz

### 11.1 InfluxDB HTTP API

**Health Check:**
```bash
curl http://localhost:8086/health
```

**Query (Flux):**
```bash
curl -X POST http://localhost:8086/api/v2/query \
  -H "Authorization: Token vehicle-admin-token" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"vehicle_data") |> range(start:-1h)'
```

**Write (Line Protocol):**
```bash
curl -X POST "http://localhost:8086/api/v2/write?org=vehicle_org&bucket=vehicle_data&precision=ns" \
  -H "Authorization: Token vehicle-admin-token" \
  -H "Content-Type: text/plain" \
  -d 'vehicle_state,vehicle_id=CAR001,state=idle fuel_l=45.5,battery_v=12.8,online=1i'
```

### 11.2 Grafana API

**Dashboards auflisten:**
```bash
curl -u admin:admin http://localhost:3001/api/search
```

**Dashboard exportieren:**
```bash
curl -u admin:admin http://localhost:3001/api/dashboards/uid/smart-car-main
```

### 11.3 Node-RED API

**Flows exportieren:**
```bash
curl http://localhost:1880/flows
```

---

## Anhang

### A. Umgebungsvariablen

| Variable | Dienst | Beschreibung |
|----------|--------|--------------|
| DOCKER_INFLUXDB_INIT_USERNAME | InfluxDB | Admin-Benutzer |
| DOCKER_INFLUXDB_INIT_PASSWORD | InfluxDB | Admin-Passwort |
| DOCKER_INFLUXDB_INIT_ORG | InfluxDB | Organisation |
| DOCKER_INFLUXDB_INIT_BUCKET | InfluxDB | Standard-Bucket |
| DOCKER_INFLUXDB_INIT_ADMIN_TOKEN | InfluxDB | API-Token |
| GF_SECURITY_ADMIN_PASSWORD | Grafana | Admin-Passwort |

### B. Referenzen

- [InfluxDB 2.x Dokumentation](https://docs.influxdata.com/influxdb/v2/)
- [Grafana Dokumentation](https://grafana.com/docs/grafana/latest/)
- [Node-RED Dokumentation](https://nodered.org/docs/)
- [Eclipse Mosquitto](https://mosquitto.org/documentation/)
- [ESP32 Arduino Core](https://docs.espressif.com/projects/arduino-esp32/)
- [LoRa Library](https://github.com/sandeepmistry/arduino-LoRa)

---

*Dokumentation erstellt: Januar 2026*
*Version: 1.0*
