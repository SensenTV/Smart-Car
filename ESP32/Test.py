from machine import Pin, SoftI2C # Wichtig: SoftI2C statt I2C
import oled as ssd1306        # Deine Datei heißt oled.py
import time

# --- PIN-KONFIGURATION ---
# Falls es ein Heltec V2 ist: SDA=4, SCL=15, RST=16
# Falls es ein Heltec V3 ist: SDA=17, SCL=18, RST=21
# Falls es ein TTGO LoRa32 ist: SDA=21, SCL=22, RST=keiner (Zeile auskommentieren)

SDA_PIN = 4   
SCL_PIN = 15  
RST_PIN = 16  

# 1. Reset-Zyklus (Zwingend notwendig für viele LoRa-Boards!)
if 'RST_PIN' in locals():
    reset = Pin(RST_PIN, Pin.OUT)
    reset.value(0)
    time.sleep(0.1)
    reset.value(1)
    time.sleep(0.1)

# 2. I2C Bus initialisieren (mit SoftI2C)
# Wir nutzen eine Frequenz von 400kHz für das Display
i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=400000)

# 3. Test: Scannt den Bus
devices = i2c.scan()
print("I2C Geräte gefunden:", devices)

if not devices:
    print("KEIN DISPLAY GEFUNDEN! Prüfe die Pins SDA und SCL.")
else:
    # 4. Display initialisieren
    # 0x3c ist die Standard-Adresse für OLEDs
    display = ssd1306.SSD1306_I2C(128, 64, i2c)

    # 5. Etwas anzeigen
    display.fill(0)
    display.text("Es geht!", 0, 0)
    display.text("LoRa ESP32", 0, 20)
    display.show()