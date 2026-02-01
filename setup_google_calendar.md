# Google Sheets Kalender-Integration Setup

## Schritt 1: Google Sheet erstellen

1. Gehe zu https://sheets.google.com
2. Erstelle ein neues Sheet mit dem Namen: **Smart-Car Termine**
3. Benenne das erste Tabellenblatt um zu: **Termine**
4. Erstelle folgende Spalten in Zeile 1:

| A | B | C | D |
|---|---|---|---|
| Uhrzeit | Aufgabe | Fahrzeug | Status |

5. Fuege Beispieldaten hinzu:

| Uhrzeit | Aufgabe | Fahrzeug | Status |
|---------|---------|----------|--------|
| 09:00 | Inspektion | CAR001 | Geplant |
| 10:30 | Oelwechsel | CAR002 | Geplant |
| 14:00 | Reifenwechsel | CAR001 | Geplant |
| 15:30 | TUeV Vorbereitung | CAR003 | Geplant |

## Schritt 2: Sheet mit Service Account teilen

1. Klicke oben rechts auf "Teilen"
2. Fuege diese E-Mail hinzu:
   ```
   inhaber-smart-car@smart-car-485709.iam.gserviceaccount.com
   ```
3. Waehle "Betrachter" oder "Bearbeiter"
4. Klicke "Senden"

## Schritt 3: Spreadsheet-ID kopieren

Die URL deines Sheets sieht so aus:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

Kopiere die SPREADSHEET_ID (der lange Text zwischen /d/ und /edit)

Beispiel:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       Das ist die Spreadsheet-ID
```

## Schritt 4: ID in Grafana eintragen

1. Oeffne Grafana: http://localhost:3000 (oder 3001)
2. Gehe zum Dashboard "Flottenuebersicht"
3. Klicke auf das Panel "Heutige Termine (Google Sheets)"
4. Klicke "Edit"
5. Im Query-Bereich:
   - **Spreadsheet ID**: Fuege deine kopierte ID ein
   - **Range**: Termine!A:D (sollte schon eingetragen sein)
6. Klicke "Apply"
7. Speichere das Dashboard

## Alternative: Automatische Kalender-Sync

Wenn du Google Calendar direkt mit Google Sheets verbinden willst:

### Google Apps Script erstellen:

1. Oeffne dein Google Sheet
2. Gehe zu: Erweiterungen -> Apps Script
3. Loesche den vorhandenen Code und fuege diesen ein:

```javascript
function syncCalendarToSheet() {
  var calendarId = 'primary'; // Oder deine Kalender-ID
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Termine');
  
  // Heute und morgen
  var today = new Date();
  today.setHours(0, 0, 0, 0);
  var tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  
  // Events holen
  var calendar = CalendarApp.getCalendarById(calendarId);
  var events = calendar.getEvents(today, tomorrow);
  
  // Sheet leeren (ausser Header)
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 1, lastRow - 1, 4).clear();
  }
  
  // Events eintragen
  for (var i = 0; i < events.length; i++) {
    var event = events[i];
    var startTime = Utilities.formatDate(event.getStartTime(), 'Europe/Berlin', 'HH:mm');
    var title = event.getTitle();
    
    // Fahrzeug aus Titel extrahieren (Format: "Aufgabe - CAR001")
    var parts = title.split(' - ');
    var aufgabe = parts[0] || title;
    var fahrzeug = parts[1] || '';
    
    sheet.getRange(i + 2, 1).setValue(startTime);
    sheet.getRange(i + 2, 2).setValue(aufgabe);
    sheet.getRange(i + 2, 3).setValue(fahrzeug);
    sheet.getRange(i + 2, 4).setValue('Geplant');
  }
}

// Automatisch alle 15 Minuten ausfuehren
function createTrigger() {
  ScriptApp.newTrigger('syncCalendarToSheet')
    .timeBased()
    .everyMinutes(15)
    .create();
}
```

4. Speichere das Script (Strg+S)
5. Fuehre `createTrigger` einmal aus (erstellt automatischen Sync)
6. Erlaube die notwendigen Berechtigungen

## Kalender-Events Format

Erstelle Events in Google Calendar mit diesem Format:
```
Inspektion - CAR001
Oelwechsel - CAR002
TUeV Pruefung - CAR003
```

Das Script trennt automatisch Aufgabe und Fahrzeug.

## Status-Farben in Grafana

| Status | Farbe |
|--------|-------|
| Geplant | Blau |
| In Bearbeitung | Gelb |
| Abgeschlossen | Gruen |
| Abgesagt | Rot |

## Fehlerbehebung

### "No data" im Panel?
1. Pruefe ob das Sheet mit dem Service Account geteilt ist
2. Pruefe die Spreadsheet-ID
3. Pruefe ob das Tabellenblatt "Termine" heisst

### Datasource-Fehler?
```bash
docker logs grafana | Select-String -Pattern "googlesheets|error"
```

### Grafana neustarten
```bash
docker restart grafana
```
