from machine import Pin, SoftSPI
from mcp2515 import MCP2515, CANFrame  # <--- HIER war der Fehler (CANFrame ergänzt)
import time

# --- PINS (Heltec V2) ---
SCK_PIN = 25
MOSI_PIN = 33
MISO_PIN = 32
CS_PIN = 17 

# --- SPI INITIALISIERUNG ---
spi = SoftSPI(baudrate=1000000, polarity=0, phase=0, 
              sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))

# --- MCP2515 INITIALISIERUNG ---
# Wichtig: Prüfe, ob dein Quarz 8MHz oder 16MHz ist (8.000 oder 16.000 steht drauf)
can = MCP2515(spi, Pin(CS_PIN), crystal=8000000) 

def test_can():
    try:
        can.reset()
        can.set_bitrate(500000) 
        can.set_mode(0) # Normaler Modus
        print("MCP2515 erfolgreich initialisiert!")
        
        # Erstelle ein Frame-Objekt (ID=0x123, Daten als Liste oder bytes)
        meine_nachricht = CANFrame(0x123, [0x11, 0x22, 0x33, 0x44])
        
        # Nachricht senden
        can.send_message(meine_nachricht)
        print("Nachricht 0x123 erfolgreich gesendet!")
        
    except Exception as e:
        print("Fehler beim Senden:", e)

if __name__ == "__main__":
    test_can()