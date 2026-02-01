import time
import sys
from machine import Pin, SoftSPI
from mcp2515 import MCP2515

# ==========================================
# HARDWARE CONFIG
# ==========================================
# Überprüfe diese Pins noch einmal genau auf deinem Board!
SCK, MOSI, MISO = 14, 13, 12
CS = 17
INT_PIN = 21 

# Dein Quarz ist 8 MHz (steht auf dem silbernen Bauteil am blauen Board)
QUARZ = 8000000 

# Standard für VW, Audi, BMW etc. ist 500000. 
# Falls nichts kommt, probiere später 250000.
SPEED = 500000

# LED blinkt, wenn ECHTE Daten vom Auto kommen
led = Pin(25, Pin.OUT)

# ==========================================
# SETUP
# ==========================================
spi = SoftSPI(baudrate=1000000, sck=Pin(SCK), mosi=Pin(MOSI), miso=Pin(MISO))
can = MCP2515(spi, Pin(CS), crystal=QUARZ)
interrupt = Pin(INT_PIN, Pin.IN)

def setup():
    try:
        can.reset()
        can.set_bitrate(SPEED)
        
        # WICHTIG: Wir starten im "Listen Only" Modus (3).
        # Das ist sicher für das Auto.
        can.set_mode(3) 
        
    except Exception:
        # Fehler ignorieren, um SavvyCAN nicht zu stören
        pass

def loop():
    # Kurze Wartezeit für SavvyCAN Reset
    time.sleep(1.0)
    
    while True:
        # Wir warten auf das Signal vom Chip (Pin 21 LOW)
        # Wenn hier nichts passiert, empfängt der Chip nichts.
        if interrupt.value() == 0:
            try:
                msg = can.read_message()
                if msg:
                    # LED kurz anmachen -> Wir haben Daten!
                    led.value(1)
                    
                    # SLCAN Formatierung für SavvyCAN
                    cmd = "T" if msg.is_extended_id else "t"
                    
                    if msg.is_extended_id:
                        id_str = "{:08X}".format(msg.arbitration_id)
                    else:
                        id_str = "{:03X}".format(msg.arbitration_id)
                    
                    dlc = str(len(msg.data))
                    data = "".join("{:02X}".format(b) for b in msg.data)
                    
                    # Senden
                    sys.stdout.write(cmd + id_str + dlc + data + '\r')
                    
                    led.value(0)
            except:
                pass

if __name__ == "__main__":
    setup()
    loop()