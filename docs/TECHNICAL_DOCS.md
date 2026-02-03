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
| **Integration** | Google Calendar | v3 | Kalender-Integration |
| **Backend** | Python/Flask | 3.11 | Calendar Webhook Server |
| **Sync** | Python Scripts | 3.11 | Fahrzeugdaten-Synchronisation |
| **Orchestrierung** | Docker Compose | 3.8 | Container-Management |

### 1.3 Netzwerk-Topologie

```
+-------------------------------------------------------------------------+
|                         Docker Network                                  |
|                       (smartcar-network)                                |
|                                                                         |
|  +-----------+   +-----------+   +-----------+   +----------------+     |
|  | mosquitto |   |  node-red |   | influxdb  |   | calendar-      |     |
|  |  :1883    |<--|   :1880   |-->|  :8086    |   | webhook :5000  |     |
|  +-----------+   +-----+-----+   +-----+-----+   +--------^-------|     |
|        |               |               |                  |             |
|        |               |               |                  |             |
|        |               v               v                  |             |
|        |         +-----+-----+   +-----v-----+            |             |
|        |         | vehicle-  |   |  grafana  |            |             |
|        |         | sync      |   |  :3001    |            |             |
|        |         +-----------+   +-----------+            |             |
+--------+-------------------------------------------------+--------------+
         |                                                  |
         | Port 1883 (TLS)                           HTTP Webhook
         v                                                  |
  +-----------+                                             v
  |   ESP32   |                                   Google Calendar API
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

# Anonyme Verbindungen erlaubt
allow_anonymous true
```

**Ports**:
| Port | Protokoll | Verwendung |
|------|-----------|------------|
| 1883 | MQTT | Kommunikation (Node-RED / ESP32) |


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
|   +-- vehicle-detail-dashboard.json # Einzelne Fahrzeugdaten
|-- datasources/
|   +-- datasources.yml        # Datenquellen
+-- alerting/
    |-- alert-rules.yml        # Alert-Regeln
    |-- contact-points.yml     # Benachrichtigungsziele
    +-- notification-policies.yml  # Benachrichtigungsrichtlinien
```

### 2.5 Calendar Webhook Server

**Funktion**: Google Calendar Integration fuer Alerts und Termine

**Technologie**: Python 3.11 + Flask

**Konfiguration**:
- Service Account Key: `/config/google-calendar-key.json`
- Alerts Config: `/config/alerts.json`
- Port: 5000

**API-Endpunkte**:
| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/health` | GET | Health Check |
| `/event` | POST | Kalendereintrag erstellen |
| `/test` | GET | Test-Event erstellen |

**Anforderungen**:
- Google Cloud Service Account mit Calendar API-Berechtigung
- Kalender muss mit Service Account geteilt sein

### 2.6 Vehicle Sync Service

**Funktion**: Periodische Synchronisation von Fahrzeugdaten mit InfluxDB

**Technologie**: Python 3.11

**Konfiguration** (`config/vehicles.json`):
```json
{
  "vehicles": [
    {
      "id": "F001",
      "name": "Fahrzeug 1",
      "fuel_capacity": 60.0,
      "battery_nominal": 12.0
    }
  ]
}
```

**Funktionalitaet**:
- Liest Fahrzeugkonfiguration aus JSON
- Schreibt initiale Daten in InfluxDB
- Stellt sicher, dass Fahrzeuge in InfluxDB vorhanden sind

---

## 3. Datenfluss

### 3.1 End-to-End Flow

```
ESP32 Sensor  -->  MQTT Publish  -->  Mosquitto  -->  Node-RED Subscribe
                                                           |
                                                           v
                                                     CSV Parsing
                                                           |
                                      +--------------------+--------------------+
                                      |                                         |
                                      v                                         v
                              Line Protocol                              Alert Detection
                                      |                                         |
                                      v                                         v
                                HTTP POST                              Calendar Webhook
                                      |                                         |
                                      v                                         v
                                  InfluxDB                            Google Calendar API
                                      |                                         |
                                      v                                         v
                                  Grafana                                 Termin erstellt
```

### 3.2 Alert-Workflow

```
MQTT Alert  -->  Node-RED  -->  Alert-Regeln pruefen  -->  Calendar Webhook
                                                                    |
                                                                    v
                                                         Google Calendar Event
                                                                    |
                                                                    v
                                                            Email/Notification
```

### 3.3 Latenz-Erwartungen

| Strecke | Erwartete Latenz |
|---------|------------------|
| ESP32 --> Mosquitto | 10-50ms (WLAN) |
| Mosquitto --> Node-RED | < 5ms |
| Node-RED --> InfluxDB | 5-20ms |
| Node-RED --> Calendar Webhook | 10-50ms |
| Calendar Webhook --> Google API | 100-500ms |
| InfluxDB --> Grafana | 50-200ms (Query) |
| **Gesamt (Telemetrie)** | **< 300ms** |
| **Gesamt (Alarm mit Kalender)** | **< 600ms** |

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
| state_name | String | Fahrzeugzustand | driving, parked |
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

### 6.1 Hauptflows

#### Flow 1: MQTT --> InfluxDB
```
[MQTT In] --> [Function: CSV zu Line Protocol] --> [HTTP Request: InfluxDB] --> [Debug]
```

#### Flow 2: Alert Detection --> Google Calendar
```
[MQTT In] --> [Function: CSV Parser] --> [Switch: Alert Filter] --> [Function: Event Builder] --> [HTTP Request: Calendar Webhook] --> [Debug]
```

#### Flow 3: Vehicle Sync Trigger
```
[Inject: On Start] --> [HTTP Request: vehicle-sync] --> [Debug]
```

### 6.2 CSV Parser Logik

- Die Topic-Adresse der eingehenden Nachricht wird anhand von „/“ aufgeteilt.
--> ```let topicParts = msg.topic.split('/');```

- Aus dem zweiten Teil des Topics wird die Fahrzeug-ID gelesen. Falls keine vorhanden ist, wird „UNKNOWN“ verwendet.
--> ```let vehicle_id = topicParts[1] || 'UNKNOWN';```

- Der Nachrichteninhalt wird in einen Text umgewandelt, von Leerzeichen bereinigt und an den Kommas getrennt.
- Dadurch entsteht eine Liste von Werten (Spalten).
--> ```let cols = msg.payload.toString().trim().split(',');```

- Der erste Wert bestimmt den Datentyp (z. B. state, error, trip, gps, alert).

- Dieser Typ wird in Kleinbuchstaben umgewandelt, um Vergleichsfehler zu vermeiden.
--> ```let type = cols[0].toLowerCase();```

- Es wird ein Zeitstempel in Nanosekunden erzeugt, basierend auf der aktuellen Zeit.
--> ```let ts = Date.now() * 1000000;```

### 6.3 HTTP Request Konfiguration

#### InfluxDB Write
- **URL**: `http://influxdb:8086/api/v2/write?org=vehicle_org&bucket=vehicle_data&precision=ns`
- **Methode**: POST
- **Headers**: Authorization Token

#### Calendar Webhook
- **URL**: `http://calendar-webhook:5000/event`
- **Methode**: POST
- **Headers**: Content-Type: application/json
- **Body**: JSON-Event-Objekt

**Event-Format**:
```json
{
  "summary": "[ALARM] Fahrzeug F001 - Kraftstoff niedrig",
  "description": "Kraftstoffstand unter 10 Liter. Fahrzeug: F001",
  "duration_minutes": 30,
  "colorId": "11"
}
```

### 6.4 Alert-Regeln Konfiguration

**Datei**: `config/alerts.json`

```json
{
  "google_calendar": {
    "enabled": true,
    "calendar_id": "iotwssmartcar@gmail.com"
  },
  "alerts": {
    "fuel_low": {
      "enabled": true,
      "threshold": 10.0,
      "severity": "HOCH",
      "calendar_duration": 30
    },
    "battery_low": {
      "enabled": true,
      "threshold": 11.5,
      "severity": "MITTEL",
      "calendar_duration": 15
    },
    "error_detected": {
      "enabled": true,
      "severity": "KRITISCH",
      "calendar_duration": 60
    }
  }
}
```

---

## 7. Grafana Dashboards

### 7.1 Hauptdashboard (Flottenuebersicht)

**UID**: `smart-car-main`

**Panels:**
1. **Aktive Fahrzeuge** (Stat)
   - Zeigt Anzahl der aktiven Fahrzeuge

2. **Aktive Fehler** (Stat)
   - Anzahl nicht geloester Fehler

3. **Fahrten 7 Tage** (Stat)
   - Anzahl Fahrten in den letzten 24 Stunden

4. **Fehler 7 Tage** (Stat)
   - Anzahl Alarme in den letzten 24 Stunden

5. **Flottenstatus** (Stat)
   - Gesamtstatus der Flotte basierend auf kritischen Werten

6. **Kraftstoff niedrig** (Stat)
   - Anzahl Fahrzeuge mit niedrigem Kraftstoff

7. **Batterie niedrig** (Stat)
   - Anzahl Fahrzeuge mit niedriger Batterie

8. **Heutige Termine** (Table)
    - Tabelle mit den anliegenden Aufgaben des aktuellen Tages

9. **Letzte Fahrten** (Table)
   - Liste der letzten Fahrten

10. **Geschwindigkeitsverlauf** (Time Series)
   - Ablaufdiagramm der Geschwindigkeiten eines Trips


### 7.2 Detail-Dashboard (Fahrzeug Details)

**UID**: `smart-car-detail`

**Variablen:**
- `$vehicle_id` - Ausgewaehltes Fahrzeug (Dropdown)

**Panels:**
1. Fahrzeug-ID(Dropdown Menue)
2. Status (Stat)
3. Kraftstoff (Gauge)
4. Batterie (Gauge)
5. Fahrten 7 Tage (Stat)
6. Kraftstoffverlauf (Time Series)
7. Batterieverlauf (Time Series)
8. Letzte Fahrten (Table)
9. Fahrzeugfehler (Table)

### 7.3 Dashboard-Provisioning

## dashboards.yml

- Die Datei dient zur automatischen Bereitstellung von Dashboards in  Grafana.

- Mit apiVersion: 1 wird festgelegt, welche Version der Provisioning-Schnittstelle verwendet wird.

- Unter „providers“ wird definiert, woher Grafana die Dashboards laden soll.

- Es wird ein Anbieter mit dem Namen „default“ angelegt.

- Die Dashboards werden in einem Ordner mit dem Namen „Smart-Car“ gespeichert und angezeigt.

- Der Typ „file“ bedeutet, dass die Dashboards aus Dateien im Dateisystem geladen werden.

- Unter „options“ wird der Speicherort der Dashboard-Dateien angegeben.

- Der Pfad /etc/grafana/provisioning/dashboards gibt an, in welchem Verzeichnis die JSON-Dashboard-Dateien liegen.

- Beim Start von Grafana werden alle Dashboards aus diesem Ordner automatisch eingelesen.

- Dadurch müssen Dashboards nicht manuell im Webinterface importiert werden, sondern stehen direkt zur Verfügung.

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

### 11.1 Calendar Webhook API

**Base URL**: `http://calendar-webhook:5000` (intern) oder `http://localhost:5000` (extern)

#### Health Check
```bash
curl http://localhost:5000/health
```

**Response**:
```json
{
  "status": "ok",
  "google_api": true
}
```

#### Event erstellen
```bash
curl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Test Event",
    "description": "Test-Beschreibung",
    "duration_minutes": 30
  }'
```

**Response (Erfolg)**:
```json
{
  "success": true,
  "event_id": "abc123...",
  "link": "https://calendar.google.com/..."
}
```

**Response (Fehler)**:
```json
{
  "success": false,
  "error": "Fehlerbeschreibung"
}
```

#### Test-Event
```bash
curl http://localhost:5000/test
```

### 11.2 InfluxDB HTTP API

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

### 11.3 Grafana API

**Dashboards auflisten:**
```bash
curl -u admin:admin http://localhost:3001/api/search
```

**Dashboard exportieren:**
```bash
curl -u admin:admin http://localhost:3001/api/dashboards/uid/smart-car-main
```

### 11.4 Node-RED API

**Flows exportieren:**
```bash
curl http://localhost:1880/flows
```

### 11.5 Vehicle Sync Service

**Fahrzeuge synchronisieren:**
```bash
docker exec vehicle-sync python /app/sync_vehicles.py
```

Oder via HTTP (wenn service läuft):
```bash
curl -X POST http://localhost:8080/sync
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
| GOOGLE_KEY_FILE | calendar-webhook | Service Account Key Pfad |
| ALERTS_FILE | calendar-webhook | Alert-Konfiguration Pfad |

### B. Konfigurationsdateien

| Datei | Beschreibung |
|-------|--------------|
| `config/alerts.json` | Alert-Regeln und Calendar-Konfiguration |
| `config/vehicles.json` | Fahrzeugdaten und -konfiguration |
| `config/google-calendar-key.json` | Google Service Account Key |
| `docker-compose.yml` | Container-Orchestrierung |
| `node-red/flows.json` | Node-RED Flows |
| `node-red/flows_cred.json` | Verschluesselte Credentials |
| `mosquitto/config/mosquitto.conf` | MQTT Broker Konfiguration |

### D. Google Calendar Integration

#### Service Account Setup

1. **Google Cloud Console**: [console.cloud.google.com](https://console.cloud.google.com)
2. Projekt erstellen/auswählen
3. **APIs & Services** → **Library** → **Google Calendar API** aktivieren
4. **IAM & Admin** → **Service Accounts** → Service Account erstellen
5. Key erstellen (JSON) → als `google-calendar-key.json` speichern
6. Kalender mit Service Account Email teilen (Berechtigungen: Änderungen vornehmen und Freigabe verwalten)

#### Event-Farbcodes

| colorId | Farbe | Verwendung |
|---------|-------|------------|
| 9 | Blau | Standard-Alarme |
| 6 | Orange | HOCH Priorität |
| 11 | Rot | KRITISCH Priorität |
| 10 | Grün | Erfolgreiche Aktionen |

#### Troubleshooting Calendar

**Fehler: "Invalid JWT Signature"**
- Service Account Key ist ungültig oder abgelaufen
- Lösung: Neuen Key erstellen und in `google-calendar-key.json` ersetzen
- Container neustarten: `docker restart calendar-webhook`

**Fehler: "Calendar not found"**
- Kalender ist nicht mit Service Account geteilt
- Lösung: In Google Calendar Kalender freigeben für Service Account Email

**Fehler: "API not enabled"**
- Google Calendar API ist nicht aktiviert
- Lösung: In Google Cloud Console API aktivieren

### E. Backup und Wiederherstellung

#### InfluxDB Backup
```bash
# Backup erstellen
docker exec influxdb influx backup /backup -t vehicle-admin-token

# Backup aus Container kopieren
docker cp influxdb:/backup ./influxdb-backup
```

#### InfluxDB Restore
```bash
# Backup in Container kopieren
docker cp ./influxdb-backup influxdb:/restore

# Restore durchführen
docker exec influxdb influx restore /restore -t vehicle-admin-token
```

#### Grafana Dashboards Backup
```bash
# Alle Dashboards exportieren
curl -u admin:admin http://localhost:3001/api/search?type=dash-db | \
  jq -r '.[] | .uid' | \
  xargs -I {} curl -u admin:admin http://localhost:3001/api/dashboards/uid/{} > dashboard-{}.json
```

#### Node-RED Flows Backup
```bash
# Flows sichern
cp node-red/flows.json node-red/flows_backup_$(date +%Y%m%d).json
cp node-red/flows_cred.json node-red/flows_cred_backup_$(date +%Y%m%d).json
```

### F. Referenzen

| Service | Port (Host) | Port (Container) | Zugriff |
|---------|-------------|------------------|---------|
| Mosquitto (MQTT) | 1883 | 1883 | Intern/Extern |
| Node-RED | 1880 | 1880 | Web-UI |
| InfluxDB | 8086 | 8086 | API |
| Grafana | 3001 | 3000 | Web-UI |
| Calendar Webhook | 5000 | 5000 | API (intern) |

### D. Externe Dokumentationen

- [InfluxDB 2.x Dokumentation](https://docs.influxdata.com/influxdb/v2/)
- [Grafana Dokumentation](https://grafana.com/docs/grafana/latest/)
- [Node-RED Dokumentation](https://nodered.org/docs/)
- [Eclipse Mosquitto](https://mosquitto.org/documentation/)
- [ESP32 Arduino Core](https://docs.espressif.com/projects/arduino-esp32/)
- [LoRa Library](https://github.com/sandeepmistry/arduino-LoRa)

