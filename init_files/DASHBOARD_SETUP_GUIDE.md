# Google Calendar Integration für Grafana Dashboard

## Übersicht
Dieses Dashboard unterstützt die Integration von Google Calendar zur Anzeige des täglichen Arbeitsplans.

### Schritt 1: Google Cloud Project Setup

1. Gehe zu https://console.cloud.google.com/
2. Erstelle ein neues Projekt: "Smart-Car"
3. Aktiviere die **Google Sheets API** und **Google Calendar API**
4. Gehe zu "Service Accounts" → Erstelle einen neuen Service Account
5. Generiere einen JSON-Schlüssel für den Service Account
6. Laden Sie den Schlüssel herunter und speichern Sie ihn sicher

### Schritt 2: Grafana Konfiguration

1. Melde dich in Grafana an (Port 3001)
2. Gehe zu Configuration → Data Sources
3. Füge eine neue Datasource hinzu:
   - **Type:** Grafana Google Sheets Datasource
   - **Authentication Type:** JWT (Service Account)
   - **Private Key:** Kopiere den Inhalt des heruntergeladenen JSON-Schlüssels

### Schritt 3: Google Calendar freigeben

1. Gehe zu https://calendar.google.com/
2. Erstelle einen neuen Kalender oder verwende einen existierenden
3. Teile den Kalender mit der E-Mail des Service Accounts (aus dem JSON-Schlüssel)
4. Gebe dem Service Account mindestens "Read" Berechtigung

### Schritt 4: Daten in Google Sheets exportieren

Um die Kalendereinträge im Dashboard anzuzeigen, erstellen Sie eine Google Sheet mit dieser Struktur:

```
Uhrzeit | Aufgabe | Fahrzeug | Status
--------|---------|----------|--------
09:00   | Inspektion CAR001 | CAR001 | Geplant
10:30   | Wartung CAR002 | CAR002 | In Bearbeitung
14:00   | Reparatur CAR003 | CAR003 | Geplant
```

Diese Sheet kann manuell erstellt oder über Google Apps Script automatisiert werden.

### Schritt 5: Dashboard konfigurieren

Die Dasboards sind bereits mit InfluxDB vorkonfiguriert:
- **Hauptdashboard:** Zeigt alle Fahrzeuge und deren Status
- **Fahrzeug-Detail:** Zeigt detaillierte Metriken für ein ausgewähltes Fahrzeug

## InfluxDB Datenstruktur

Das Dashboard erwartet folgende Messwerte in InfluxDB:

### vehicles (Fahrzeugliste)
- vehicle_id
- status
- last_error
- error_timestamp

### vehicle_metrics (Echtzeitmetriken)
- temperature (Motortemperatur)
- battery_level (Batteriestand)
- speed (Geschwindigkeit)

### error_logs (Fehlerprotokoll)
- error_code
- error_message
- severity
- timestamp

### vehicle_errors (Fehler Zeitserie)
- error_count

## Automatische Dashboard-Synchronisation

Die Dashboards werden automatisch aus den JSON-Dateien geladen:
- `/grafana/provisioning/dashboards/main-dashboard.json`
- `/grafana/provisioning/dashboards/vehicle-detail-dashboard.json`

Bei Änderungen müssen die Docker-Container nicht neu gestartet werden (AutoReload ist aktiviert).

## Tipps

1. **Interaktive Links:** Klicke auf ein Fahrzeug in der Übersichtstabelle, um zum Detail-Dashboard zu wechseln
2. **Zeitbereich:** Nutze den Zeitwähler oben rechts, um verschiedene Zeiträume zu analysieren
3. **Variablen:** Das Detail-Dashboard nutzt Variable für die Fahrzeug-Filterung
4. **Grafana Plugins:** Installiere ggf. zusätzliche Plugins wie "Discrete" für bessere Darstellung

## Docker-Compose Update

Wenn Sie Google Sheets Datasource nutzen möchten, laden Sie das Plugin nach dem Start:

```bash
docker exec grafana grafana-cli plugins install grafana-googlesheets-datasource
docker restart grafana
```

