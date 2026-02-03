# ESP32 CAN-Bus Debug Anleitung
# ==============================

## Vorbereitete Test-Scripts

Du hast jetzt 4 Test-Scripts. Führe sie in dieser Reihenfolge aus:

### 1. `hardware_check.py` - ZUERST ausführen
Testet grundlegende Hardware OHNE Auto-Verbindung:
- ESP32 GPIO Pins
- SPI Bus Funktionalität  
- MCP2515 Chip-Erkennung

**Erwartetes Ergebnis:** "MCP2515 GEFUNDEN!" mit Pins

---

### 2. `loopback_test.py` - OHNE Auto
Testet den MCP2515 im Loopback-Modus (sendet sich selbst):
- Kein CAN-Bus nötig
- Prüft ob der Chip funktioniert

**Erwartetes Ergebnis:** "LOOPBACK TEST BESTANDEN!"

---

### 3. `can_mega_debug.py` - AM AUTO
Das Hauptscript - testet ALLE Kombinationen:
- 3 Pin-Konfigurationen
- 6 Timing-Kombinationen (8MHz/16MHz × 3 Bitraten)
- Lauscht jeweils 5 Sekunden

**Erwartetes Ergebnis:** Funktionierende Konfiguration mit Nachrichten

---

### 4. `debug_can.py` - Schnelltest
Einfacher Test mit einer Konfiguration (5 Sekunden lauschen)

---

## Checkliste für den Auto-Test

### Hardware-Verbindung

```
ESP32 (Heltec V2)         MCP2515 Modul
-----------------------------------------
3.3V oder 5V    ------>   VCC (*)
GND             ------>   GND
GPIO 25         ------>   SCK
GPIO 33         ------>   SI (MOSI)
GPIO 32         ------>   SO (MISO)
GPIO 17         ------>   CS
                          INT (optional)

(*) WICHTIG: Blaue Module brauchen oft 5V!
    Wenn du nur 3.3V hast, funktioniert es evtl. nicht.
```

### MCP2515 → Auto (OBD2)

```
MCP2515 Modul             OBD2 Stecker
-----------------------------------------
CAN-H           ------>   Pin 6  (oben, 3. von links)
CAN-L           ------>   Pin 14 (unten, 5. von links)

OBD2 Pinout (Blick von vorne):

    1   2   3   4   5   6   7   8
   [ ] [ ] [ ] [ ] [ ] [H] [ ] [ ]
   [ ] [ ] [ ] [ ] [ ] [L] [ ] [ ]
     9  10  11  12  13  14  15  16

Farben am MCP2515 Modul:
- CAN-H = oft GELB oder ORANGE
- CAN-L = oft GRÜN oder BLAU
- Manche haben nur H und L Beschriftung
```

### Vor dem Test prüfen

- [ ] Zündung AN (Position II, Motor muss nicht laufen)
- [ ] Bei manchen Autos: Tür offen lassen
- [ ] OBD2 Stecker fest eingesteckt
- [ ] CAN-H und CAN-L nicht vertauscht
- [ ] ESP32 hat Strom (USB oder Batterie)

### Typische Quarz-Frequenzen

Schau auf den Metallquader auf deinem MCP2515 Modul:
- **8.000** = 8 MHz
- **16.000** = 16 MHz

### Typische Bitraten nach Fahrzeugtyp

| Fahrzeug | HS-CAN Bitrate |
|----------|----------------|
| VW/Audi/Skoda/Seat | 500 kbps |
| BMW | 500 kbps |
| Mercedes | 500 kbps |
| Ford | 500 kbps (manchmal 125k) |
| Toyota | 500 kbps |
| Honda | 500 kbps |
| Opel | 500 kbps |
| Ältere Autos (<2008) | oft 250 kbps oder 125 kbps |

---

## So führst du die Scripts aus

### Mit Thonny:
1. Öffne Thonny
2. Verbinde mit ESP32
3. Öffne das Script
4. Klicke "Run"

### Mit ampy:
```bash
# Script hochladen und als main.py ausführen
ampy --port COM3 put hardware_check.py main.py
# ESP32 neu starten (Reset-Taste)

# Oder direkt ausführen:
ampy --port COM3 run hardware_check.py
```

### Mit mpremote:
```bash
mpremote connect COM3 run hardware_check.py
```

---

## Fehlerbehebung

### "Nur 0xFF gelesen"
- Keine SPI Verbindung
- Prüfe: VCC, GND, SCK, MOSI, MISO, CS
- Kabel defekt?

### "Loopback OK aber keine CAN Nachrichten"
- Bitrate falsch → Script testet automatisch mehrere
- Quarz falsch → Script testet 8MHz und 16MHz
- CAN-H/CAN-L vertauscht
- Zündung nicht an
- Auto hat MS-CAN statt HS-CAN

### "Keine Nachrichten bei allen Kombinationen"
- 120Ω Terminator nötig?
- OBD2 hat keinen CAN (ältere Autos)
- Transceiver-Problem (5V vs 3.3V)

### "Nachrichten kommen aber sehen komisch aus"
- Das ist normal! CAN-IDs sind herstellerspezifisch
- z.B. 0x7E8 = OBD2 Antwort, 0x1A0 = Motor-Daten
