# Kalender Integration - Smart-Car Alerts

Diese Anleitung erklärt, wie du automatische Kalendereinträge bekommst,
wenn dein Fahrzeug getankt werden muss, die Batterie schwach ist, etc.

## Übersicht

Das System erstellt automatisch Termine für:
- 🚗 **Tank niedrig** (< 15 Liter) → "Fahrzeug tanken"
- 🚨 **Tank kritisch** (< 8 Liter) → "DRINGEND: Fahrzeug tanken!"
- 🔋 **Batterie schwach** (< 11.8V) → "Fahrzeugbatterie prüfen"
- 🔧 **Wartung fällig** (alle 15.000 km) → "Fahrzeugwartung fällig"

---

## Option 1: Google Calendar (EMPFOHLEN - Kostenlos!)

### Schritt 1: Google Cloud Projekt erstellen

1. Gehe zu https://console.cloud.google.com
2. Oben auf **Projekt auswählen** → **Neues Projekt**
3. Name: "Smart-Car"
4. **Erstellen**

### Schritt 2: Google Calendar API aktivieren

1. Gehe zu **APIs & Dienste** → **Bibliothek**
2. Suche nach "Google Calendar API"
3. Klicke drauf → **Aktivieren**

### Schritt 3: Service Account erstellen

1. Gehe zu **APIs & Dienste** → **Anmeldedaten**
2. Klicke auf **+ Anmeldedaten erstellen** → **Dienstkonto**
3. Name: "smart-car-calendar"
4. **Erstellen und fortfahren** → **Fertig**

### Schritt 4: JSON-Schlüssel herunterladen

1. Klicke auf das erstellte Dienstkonto
2. Tab **Schlüssel** → **Schlüssel hinzufügen** → **Neuen Schlüssel erstellen**
3. Format: **JSON**
4. **Erstellen** - Datei wird heruntergeladen!
5. **Speichere die Datei als `config/google-calendar-key.json`**

### Schritt 5: Kalender mit Service Account teilen

1. Öffne https://calendar.google.com
2. Links bei deinem Kalender: **⋮** → **Einstellungen und Freigabe**
3. Unter "Für bestimmte Personen freigeben" → **+ Personen hinzufügen**
4. Füge die E-Mail des Service Accounts ein (steht in der JSON-Datei unter "client_email")
   - Sieht aus wie: `smart-car-calendar@smart-car-xxxxx.iam.gserviceaccount.com`
5. Berechtigung: **Termine ändern**
6. **Senden**

### Schritt 6: Kalender-ID kopieren

1. In den Kalender-Einstellungen unter **Kalender integrieren**
2. Kopiere die **Kalender-ID** (sieht aus wie eine E-Mail)
   - Bei deinem Hauptkalender ist es deine Gmail-Adresse
   - Bei anderen Kalendern: `xxxxx@group.calendar.google.com`

### Schritt 7: Konfiguration eintragen

Öffne `config/alerts.json` und trage ein:

```json
"google_calendar": {
  "enabled": true,
  "key_file": "/config/google-calendar-key.json",
  "calendar_id": "DEINE_KALENDER_ID_HIER"
}
```

### Schritt 8: Node-RED Google Calendar Node installieren

In Node-RED (http://localhost:1880):
1. Menü (☰) → **Palette verwalten**
2. Tab **Installation**
3. Suche: `node-red-contrib-google`
4. Installiere `node-red-contrib-google-calendar`

---

## Option 2: IFTTT (Noch einfacher, aber mit Limits)

### Schritt 1: IFTTT Account

1. Gehe zu https://ifttt.com und registriere dich (kostenlos)

### Schritt 2: Webhook erstellen

1. Gehe zu https://ifttt.com/create
2. **If This**: Wähle **Webhooks** → **Receive a web request**
3. Event Name: `smart_car_alert`
4. **Then That**: Wähle **Google Calendar** → **Quick add event**
5. Event: `{{Value1}} - {{Value2}}`
6. **Create action** → **Continue** → **Finish**

### Schritt 3: Webhook-Key finden

1. Gehe zu https://ifttt.com/maker_webhooks
2. Klicke auf **Documentation**
3. Kopiere deinen **Key**

### Schritt 4: URL zusammenbauen

Die URL ist:
```
https://maker.ifttt.com/trigger/smart_car_alert/with/key/DEIN_KEY
```

Diese URL in Node-RED eintragen (siehe unten).

---

## Node-RED Konfiguration

### Für Google Calendar (Option 1):

Die JSON-Schlüsseldatei wird automatisch geladen. Stelle sicher:
- Datei liegt in `config/google-calendar-key.json`
- Docker-Compose mountet den config-Ordner

### Für IFTTT (Option 2):

1. Öffne Node-RED: http://localhost:1880
2. Gehe zum Tab **Alerts & Kalender**
3. Doppelklicke auf **Power Automate Webhook**
4. Ändere die URL zu deiner IFTTT-URL:
   ```
   https://maker.ifttt.com/trigger/smart_car_alert/with/key/DEIN_KEY
   ```
5. **Deploy** (oben rechts)

---

## Grafana: Heutige Termine ohne Google Sheets

Wenn du lediglich deine Google-Calendar-Einträge direkt im Dashboard sehen willst, brauchst du keine zusätzliche Google-Sheet-Bridge mehr.

1. **Docker Compose aktualisieren:** Der `grafana`-Container installiert jetzt automatisch das Plugin `yesoreyeram-infinity-datasource`. Führe nach dem Pull `docker compose up -d grafana --force-recreate` aus, damit das Plugin heruntergeladen wird.
2. **Neuer Data Source Eintrag:** Unter `Connections → Data sources` findest du jetzt automatisch `Calendar Events`. Die Quelle ruft den lokalen Calendar-Webhook (`http://calendar-webhook:5000`) ab – keine weiteren Tokens nötig.
3. **Neues Endpoint testen:** Stelle sicher, dass der Webhook läuft und der Service-Account Zugriff hat:
   ```
   curl http://localhost:5000/events/today
   ```
   Du solltest eine JSON-Liste deiner heutigen Termine erhalten. Fehler wie „Google Calendar deaktiviert“ deuten auf eine fehlende `alerts.json`-Konfiguration hin.
4. **Dashboard-Panel (Frontend Parser):** Das Main-Dashboard enthält das Panel *„Heutige Termine (Google Calendar)“*. Falls du es manuell nachbauen willst, setze im Query-Editor folgende Optionen:
   - **Type:** `JSON`, **Parser:** `Frontend`, **Format:** `Table`, **Root selector:** `events`.
   - `Columns` definieren: `start_local → Start`, `end_local → Ende`, `summary → Termin`, `vehicle_hint → Fahrzeug`, `description → Beschreibung`, `status → Status`, optional `htmlLink → Link`.
   - URL bleibt `http://calendar-webhook:5000/events/today`, Methode `GET`, Cache 60 s.
   Damit landet jedes Event als Tabellenzeile, ohne dass Google Sheets nötig ist. Der Hinweis „This parser does not support backend operations …“ ist nur informativ und kann ignoriert werden, solange du keine Alert-Queries daraus baust.
5. **Alternative (JSONata Backend):** Falls du lieber einen Backend-Parser mit JSONata nutzen willst, wähle im Parser-Dropdown `Backend → JSONata` und verwende diese Expression:
   ```jsonata
   (
     $events := events;
     $events.$map(function($e) {
       {
         Start: $e.start_local,
         Ende: $e.end_local,
         Termin: $e.summary,
         Fahrzeug: $e.vehicle_hint,
         Status: $e.status,
         Beschreibung: $substring($e.description,0,120),
         Link: $e.htmlLink
       }
     })
   )
   ```
   Dadurch verschwindet die Backend-Warnung und du kannst Alerting/Sharing auf dem Panel nutzen.
6. **Eigene Filter:** Falls du mehrere Kalender einbindest, kannst du im Panel weitere Spalten (z. B. `calendar_id`) anzeigen oder im Data-Source-Query zusätzliche URL-Parameter (`?limit=10`) setzen.

---

## Testen

1. Sende Test-Alert:
```powershell
docker exec mosquitto mosquitto_pub -h localhost -t "smartcar/TEST001" -m "state,TEST001,parked,7.5,12.8"
```

2. Prüfe deinen Kalender - ein neuer Termin sollte erscheinen!

---

## Troubleshooting

### Kein Termin erstellt?
- Prüfe Node-RED Logs: `docker logs node-red`
- Prüfe ob der Service Account Schreibrechte hat
- Prüfe die Kalender-ID

### "Quota exceeded"?
- Google Calendar API hat ein kostenloses Limit von 1.000.000 Requests/Tag
- Das reicht für normale Nutzung mehr als aus

### Cooldowns zurücksetzen
Wenn du testen willst aber der Cooldown aktiv ist:
1. Node-RED öffnen
2. Tab "Alerts & Kalender"
3. Klicke auf "Cooldowns zurücksetzen"
