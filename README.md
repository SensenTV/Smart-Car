# Smart-Car IoT Platform

> IoT-basierte Fahrzeugueberwachung und -management mit ESP32, MQTT, Node-RED, InfluxDB und Grafana

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://www.docker.com/)

---

## Inhaltsverzeichnis

- [Projektuebersicht](#projektuebersicht)
- [Systemarchitektur](#systemarchitektur)
- [Features](#features)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [ESP32 Anbindung](#esp32-anbindung)
- [Datenformat](#datenformat)
- [Web-Interfaces](#web-interfaces)
- [Zugangsdaten](#zugangsdaten)
- [Projektstruktur](#projektstruktur)
- [Team](#team)

---

## Projektuebersicht

**Smart-Car** ist eine IoT-Plattform zur Echtzeit-Ueberwachung von Fahrzeugdaten. Das System empfaengt Telemetriedaten von ESP32-Mikrocontrollern ueber **WLAN (MQTT)** oder **LoRa**, verarbeitet diese in Node-RED und speichert sie in InfluxDB zur Visualisierung in Grafana.

### Anwendungsfaelle
- Echtzeit-Monitoring von Fahrzeugflotten
- Automatische Alarmierung bei Fehlern
- Historische Datenanalyse
- Batterie- und Kraftstoffueberwachung
- Fahrzeugwartungsplanung

---

## Systemarchitektur

```
+-----------------------------------------------------------------------------+
|                              SMART-CAR ARCHITEKTUR                          |
+-----------------------------------------------------------------------------+

    +---------------+         +---------------+
    |   ESP32       |         |   ESP32       |
    |   (WLAN)      |         |   (LoRa)      |
    |  +----------+ |         |  +----------+ |
    |  | Sensoren | |         |  | Sensoren | |
    |  +----------+ |         |  +----------+ |
    +-------+-------+         +-------+-------+
            | MQTT/TLS                | LoRa 868MHz
            | Port 8883               |
            v                         v
    +---------------------------------------------+
    |            MOSQUITTO MQTT                   |
    |         (Message Broker)                    |
    |   Port 1883 (intern) / 8883 (TLS)          |
    +----------------------+----------------------+
                           |
                           v
    +---------------------------------------------+
    |              NODE-RED                       |
    |         (Datenverarbeitung)                 |
    |   - CSV Parsing                             |
    |   - Alarmierung                             |
    |   - Datenvalidierung                        |
    |              Port 1880                      |
    +----------------------+----------------------+
                           |
                           v
    +---------------------------------------------+
    |             INFLUXDB 2.x                    |
    |         (Zeitreihendatenbank)               |
    |   Bucket: vehicle_data                      |
    |   Org: vehicle_org                          |
    |              Port 8086                      |
    +----------------------+----------------------+
                           |
                           v
    +---------------------------------------------+
    |              GRAFANA                        |
    |          (Visualisierung)                   |
    |   - Hauptdashboard                          |
    |   - Fahrzeug-Detail                         |
    |              Port 3001                      |
    +---------------------------------------------+
```

---

## Features

| Feature | Beschreibung |
|---------|--------------|
| **TLS-Verschluesselung** | Sichere MQTT-Kommunikation ueber Port 8883 |
| **WLAN + LoRa** | Duale Konnektivitaet fuer flexible Einsatzszenarien |
| **Echtzeit-Daten** | Live-Streaming von Fahrzeugtelemetrie |
| **Alarmsystem** | Automatische Benachrichtigungen bei Fehlern |
| **Dashboards** | Vorkonfigurierte Grafana-Visualisierungen |
| **Docker-basiert** | Einfache Installation und Portabilitaet |
| **Google Calendar** | Integration fuer Wartungsplanung |

---

## Voraussetzungen

- **Docker Desktop** (inkl. Docker Compose)
- **WSL 2** (nur Windows)
- **OpenSSL** (fuer TLS-Zertifikate)
- **Git**

### Hardware (optional fuer Fahrzeuganbindung)
- ESP32 DevKit
- LoRa-Modul (SX1276/SX1278) fuer Langstrecke
- OBD-II Adapter oder Sensoren

---

## Installation

### 1. Repository klonen
```bash
git clone https://github.com/SensenTV/Smart-Car.git
cd Smart-Car
```

### 2. TLS-Zertifikate generieren

**Windows (PowerShell):**
```powershell
.\generate-certs.ps1
```

**Linux/macOS:**
```bash
chmod +x generate-certs.sh
./generate-certs.sh
```

### 3. Docker-Container starten
```bash
docker-compose up -d
```

### 4. Installation ueberpruefen
```bash
docker-compose ps
```

Alle Container sollten den Status `Up` haben:
- influxdb
- grafana
- mosquitto
- node-red

---

## ESP32 Anbindung

### WLAN (MQTT ueber TLS)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>

// Konfiguration
const char* ssid = "DEIN_WLAN";
const char* password = "DEIN_PASSWORT";
const char* mqtt_server = "192.168.1.100";  // IP des Servers
const int mqtt_port = 8883;
const char* vehicle_id = "CAR001";

WiFiClientSecure espClient;
PubSubClient client(espClient);

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    espClient.setInsecure();  // Fuer Testzwecke
    client.setServer(mqtt_server, mqtt_port);
}

void sendVehicleState(float fuel, float battery, const char* state) {
    char topic[50];
    char payload[100];
    
    snprintf(topic, sizeof(topic), "smartcar/%s", vehicle_id);
    snprintf(payload, sizeof(payload), "state,%s,%.1f,%.2f,%s",
             vehicle_id, fuel, battery, state);
    
    client.publish(topic, payload);
}

void loop() {
    if (!client.connected()) {
        client.connect(vehicle_id);
    }
    client.loop();
    
    // Beispieldaten senden
    sendVehicleState(45.5, 12.8, "driving");
    delay(5000);
}
```

### LoRa (fuer Langstrecke)

```cpp
#include <SPI.h>
#include <LoRa.h>

// LoRa Pins (ESP32)
#define SS 18
#define RST 14
#define DIO0 26

const char* vehicle_id = "CAR002";

void setup() {
    Serial.begin(115200);
    LoRa.setPins(SS, RST, DIO0);
    
    if (!LoRa.begin(868E6)) {  // EU-Frequenz
        Serial.println("LoRa init failed!");
        while (1);
    }
    
    LoRa.setSpreadingFactor(7);
    LoRa.setSignalBandwidth(125E3);
}

void sendLoRaData(float fuel, float battery, const char* state) {
    char payload[100];
    snprintf(payload, sizeof(payload), "%s,state,%.1f,%.2f,%s",
             vehicle_id, fuel, battery, state);
    
    LoRa.beginPacket();
    LoRa.print(payload);
    LoRa.endPacket();
}

void loop() {
    sendLoRaData(45.5, 12.8, "driving");
    delay(10000);  // LoRa: laengere Intervalle
}
```

---

## Datenformat

Alle Daten werden als CSV ueber MQTT gesendet auf Topic `smartcar/{vehicle_id}`:

### Fahrzeugstatus
```
state,{vehicle_id},{state},{fuel_l},{battery_v}
```
Beispiel: `state,CAR001,driving,45.5,12.8`

### Fahrt-Zusammenfassung
```
trip,{vehicle_id},{trip_id},{duration_s},{fuel_used},{max_acc},{max_brake}
```
Beispiel: `trip,CAR001,TRIP001,3600,5.5,3.2,4.8`

### Fehler
```
error,{vehicle_id},{error_code},{active}
```
Beispiel: `error,CAR001,P0420,1`

### GPS-Position
```
gps,{vehicle_id},{latitude},{longitude},{speed_kmh}
```
Beispiel: `gps,CAR001,53.5511,9.9937,45`

### Alarm
```
alert,{vehicle_id},{alert_type},{message}
```
Beispiel: `alert,CAR001,fuel_low,Kraftstoff_unter_10L`

---

## Web-Interfaces

| Service | URL | Beschreibung |
|---------|-----|--------------|
| **Grafana** | http://localhost:3001 | Dashboards und Visualisierung |
| **Node-RED** | http://localhost:1880 | Flow-Editor und Debugging |
| **InfluxDB** | http://localhost:8086 | Datenbank-UI und Queries |

---

## Zugangsdaten

### InfluxDB
| Feld | Wert |
|------|------|
| Benutzer | `admin` |
| Passwort | `admin123` |
| Organisation | `vehicle_org` |
| Bucket | `vehicle_data` |
| Token | `vehicle-admin-token` |

### Grafana
| Feld | Wert |
|------|------|
| Benutzer | `admin` |
| Passwort | `admin` |

### MQTT (Mosquitto)
| Port | Verwendung |
|------|------------|
| 1883 | Unverschluesselt (nur intern) |
| 8883 | TLS-verschluesselt (empfohlen) |

---

## Projektstruktur

```
Smart-Car/
|-- docker-compose.yml         # Container-Orchestrierung
|-- README.md                  # Diese Datei
|-- DASHBOARD_SETUP_GUIDE.md   # Grafana-Anleitung
|-- generate-certs.ps1         # TLS-Zertifikate (Windows)
|-- generate-certs.sh          # TLS-Zertifikate (Linux/Mac)
|
|-- data/
|   |-- grafana/               # Grafana-Plugins und Daten
|   +-- influxdb/              # InfluxDB-Datenbank
|
|-- grafana/
|   +-- provisioning/
|       |-- dashboards/        # Dashboard-JSON-Dateien
|       |   |-- main-dashboard.json
|       |   +-- vehicle-detail-dashboard.json
|       +-- datasources/       # Datenquellen-Konfiguration
|
|-- mosquitto/
|   |-- config/
|   |   |-- mosquitto.conf     # MQTT-Konfiguration
|   |   +-- certs/             # TLS-Zertifikate
|   +-- log/                   # MQTT-Logs
|
|-- node-red/
|   |-- flows.json             # Node-RED Flows
|   +-- settings.js            # Node-RED Einstellungen
|
|-- esp32/                     # ESP32 Beispielcode
|   |-- wlan_mqtt_example/
|   +-- lora_example/
|
+-- docs/                      # Dokumentation
    +-- TECHNICAL_DOCS.md
```

---

## Testen

### MQTT-Verbindung testen
```bash
# Nachricht senden (ohne TLS)
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,idle,45.5,12.8"

# Nachrichten empfangen
docker exec mosquitto mosquitto_sub -t "smartcar/#" -v
```

### Python Test-Script
```bash
# Einmalige Testdaten senden
python Test/send_dummy_data.py --full-test

# Kontinuierliche Daten senden
python Test/send_dummy_data.py --continuous --with-trips
```

### InfluxDB Query
```bash
docker exec -it influxdb influx query 'from(bucket:"vehicle_data") |> range(start:-1h)'
```

---

## Team

| Name | Rolle | GitHub |
|------|-------|--------|
| **SensenTV** | Entwickler | [@SensenTV](https://github.com/SensenTV) |
| **VellGmbH** | Entwickler | [@VellGmbH](https://github.com/VellGmbH) |
| **Baris** | Entwickler | [@baris2602](https://github.com/baris2602) |

---

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.

---

## Weiterfuehrende Links

- [InfluxDB Dokumentation](https://docs.influxdata.com/)
- [Grafana Dokumentation](https://grafana.com/docs/)
- [Node-RED Dokumentation](https://nodered.org/docs/)
- [Mosquitto Dokumentation](https://mosquitto.org/documentation/)
- [ESP32 Arduino Core](https://github.com/espressif/arduino-esp32)

---

*Projekt erstellt im Rahmen des IoT-Kurses WS25/26*
