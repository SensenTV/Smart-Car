"""
Smart-Car LoRa Sender
Liest Fahrzeugdaten und sendet sie per LoRa zum Gateway.

Hardware:
- ESP32 mit LoRa (Heltec/TTGO)
- MPU6050 (Beschleunigung)
- MCP2515 (CAN-Bus, optional)
- OLED Display (optional)
"""
import time
import gc
from machine import Pin, SoftI2C, SPI
import ustruct

# Konfiguration laden
from config import (
    VEHICLE_ID, LORA_PINS, LORA_FREQUENCY, LORA_TX_POWER,
    LORA_SPREADING_FACTOR, LORA_BANDWIDTH, LORA_SYNC_WORD,
    I2C_SDA, I2C_SCL, I2C_RST,
    SEND_INTERVAL_STATE, SEND_INTERVAL_GPS, SEND_INTERVAL_IMU
)

# ===========================================
# HARDWARE INITIALISIERUNG
# ===========================================
print("=" * 40)
print("Smart-Car LoRa Sender")
print(f"Fahrzeug: {VEHICLE_ID}")
print("=" * 40)

# LED
led = Pin(LORA_PINS.get('led', 25), Pin.OUT)
led.value(0)

# OLED Display (optional)
display = None
try:
    i2c_rst = Pin(I2C_RST, Pin.OUT)
    i2c_rst.value(1)
    i2c = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
    
    # Versuche OLED zu finden
    devices = i2c.scan()
    if 0x3C in devices:
        import ssd1306
        display = ssd1306.SSD1306_I2C(128, 64, i2c)
        display.fill(0)
        display.text("Smart-Car LoRa", 0, 0)
        display.text(f"ID: {VEHICLE_ID}", 0, 16)
        display.show()
        print("OLED Display OK")
except Exception as e:
    print(f"OLED nicht verfuegbar: {e}")

# MPU6050 (Beschleunigungssensor)
mpu_available = False
try:
    if 0x68 in i2c.scan():
        i2c.writeto_mem(0x68, 0x6B, b'\x00')  # Wake up
        mpu_available = True
        print("MPU6050 OK")
except Exception as e:
    print(f"MPU6050 nicht verfuegbar: {e}")

# LoRa Modul
print("Initialisiere LoRa...")
from sx127x import SX127x

spi = SPI(1, baudrate=5000000, polarity=0, phase=0,
          sck=Pin(LORA_PINS['sck']),
          mosi=Pin(LORA_PINS['mosi']),
          miso=Pin(LORA_PINS['miso']))

lora_params = {
    'frequency': LORA_FREQUENCY,
    'tx_power_level': LORA_TX_POWER,
    'signal_bandwidth': LORA_BANDWIDTH,
    'spreading_factor': LORA_SPREADING_FACTOR,
    'coding_rate': 5,
    'preamble_length': 8,
    'implicit_header': False,
    'sync_word': LORA_SYNC_WORD,
    'enable_CRC': True,
}

lora = SX127x(spi, LORA_PINS, lora_params)
print(f"LoRa auf {LORA_FREQUENCY/1E6:.1f} MHz bereit!")

# ===========================================
# SENSOR FUNKTIONEN
# ===========================================
def read_mpu6050():
    """Liest Beschleunigungsdaten vom MPU6050"""
    if not mpu_available:
        return None
    try:
        raw = i2c.readfrom_mem(0x68, 0x3B, 6)
        ax, ay, az = [v / 16384.0 for v in ustruct.unpack('>hhh', raw)]
        return {'ax': ax, 'ay': ay, 'az': az}
    except:
        return None

def get_simulated_gps():
    """Simulierte GPS-Daten (ersetze mit echtem GPS-Modul)"""
    # TODO: GPS-Modul einbinden (z.B. NEO-6M)
    import random
    return {
        'lat': 49.2354 + random.uniform(-0.001, 0.001),  # Saarbrücken
        'lon': 7.0000 + random.uniform(-0.001, 0.001),
        'speed': random.randint(0, 80)
    }

def get_vehicle_state():
    """Ermittelt Fahrzeugzustand"""
    # TODO: Ersetze mit echten CAN-Bus Daten
    import random
    
    # Simulierte Werte
    fuel = 35.0 + random.uniform(-2, 2)
    battery = 12.8 + random.uniform(-0.3, 0.3)
    
    # Zustand basierend auf IMU
    imu = read_mpu6050()
    if imu:
        total_acc = (imu['ax']**2 + imu['ay']**2 + imu['az']**2)**0.5
        if total_acc > 1.1:  # Bewegung erkannt
            state = "driving"
        else:
            state = "parked"
    else:
        state = "unknown"
    
    return {
        'state': state,
        'fuel': fuel,
        'battery': battery
    }

# ===========================================
# NACHRICHTENFORMATE
# ===========================================
def create_state_message():
    """Erstellt State-Nachricht"""
    data = get_vehicle_state()
    return f"state,{VEHICLE_ID},{data['state']},{data['fuel']:.1f},{data['battery']:.2f}"

def create_gps_message():
    """Erstellt GPS-Nachricht"""
    gps = get_simulated_gps()
    return f"gps,{VEHICLE_ID},{gps['lat']:.6f},{gps['lon']:.6f},{gps['speed']}"

def create_imu_message():
    """Erstellt IMU-Nachricht"""
    imu = read_mpu6050()
    if not imu:
        return None
    return f"imu,{VEHICLE_ID},{imu['ax']:.3f},{imu['ay']:.3f},{imu['az']:.3f},0,0,0"

def create_error_message(code, active=1):
    """Erstellt Fehler-Nachricht"""
    return f"error,{VEHICLE_ID},{code},{active}"

# ===========================================
# DISPLAY UPDATE
# ===========================================
def update_display(msg_type, rssi=None):
    """Aktualisiert OLED Display"""
    if not display:
        return
    
    display.fill(0)
    display.text("LoRa Sender", 0, 0)
    display.text(f"ID: {VEHICLE_ID}", 0, 12)
    display.text("-" * 16, 0, 24)
    display.text(f"Gesendet: {msg_type}", 0, 36)
    
    # Statistiken
    mem_free = gc.mem_free() // 1024
    display.text(f"RAM: {mem_free}KB", 0, 52)
    display.show()

# ===========================================
# HAUPTSCHLEIFE
# ===========================================
print("\nStarte Sende-Loop...")
print("Druecke Ctrl+C zum Beenden\n")

last_state = 0
last_gps = 0
last_imu = 0
msg_count = 0

try:
    while True:
        now = time.time()
        sent_type = None
        
        # State senden (alle 10 Sekunden)
        if now - last_state >= SEND_INTERVAL_STATE:
            msg = create_state_message()
            if lora.send(msg):
                print(f"[TX] {msg}")
                sent_type = "STATE"
                msg_count += 1
            else:
                print("[ERR] State senden fehlgeschlagen")
            last_state = now
        
        # GPS senden (alle 30 Sekunden)
        elif now - last_gps >= SEND_INTERVAL_GPS:
            msg = create_gps_message()
            if lora.send(msg):
                print(f"[TX] {msg}")
                sent_type = "GPS"
                msg_count += 1
            else:
                print("[ERR] GPS senden fehlgeschlagen")
            last_gps = now
        
        # IMU senden (alle 5 Sekunden, nur wenn verfügbar)
        elif now - last_imu >= SEND_INTERVAL_IMU:
            msg = create_imu_message()
            if msg:
                if lora.send(msg):
                    print(f"[TX] {msg}")
                    sent_type = "IMU"
                    msg_count += 1
            last_imu = now
        
        # Display aktualisieren
        if sent_type:
            update_display(sent_type)
            led.value(1)
            time.sleep(0.1)
            led.value(0)
        
        # Kurze Pause
        time.sleep(0.5)
        gc.collect()

except KeyboardInterrupt:
    print(f"\n\nBeendet. {msg_count} Nachrichten gesendet.")
    lora.sleep()
