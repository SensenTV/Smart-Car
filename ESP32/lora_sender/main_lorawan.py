"""
Smart-Car LoRaWAN Sender
Sendet Fahrzeugdaten über TTN/ChirpStack Gateway.

Hardware: ESP32 mit LoRa (Heltec/TTGO)

Datenfluss:
  ESP32 (Auto) --LoRaWAN--> Uni Gateway --TTN--> Webhook --> Node-RED --> InfluxDB
"""
import time
import gc
import struct
from machine import Pin, SoftI2C, SPI
import ustruct

# Konfiguration
from config_lorawan import (
    VEHICLE_ID, DEV_EUI, JOIN_EUI, APP_KEY,
    LORA_PINS, LORA_FREQUENCY, LORA_SPREADING_FACTOR,
    LORA_TX_POWER, EU868_FREQUENCIES,
    I2C_SDA, I2C_SCL, I2C_RST,
    SEND_INTERVAL_NORMAL, SEND_INTERVAL_DRIVING,
    PORT_STATE, PORT_GPS, PORT_IMU, PORT_ERROR
)

# ===========================================
# HARDWARE INIT
# ===========================================
print("=" * 40)
print("Smart-Car LoRaWAN Sender")
print(f"Fahrzeug: {VEHICLE_ID}")
print(f"DevEUI: {DEV_EUI}")
print("=" * 40)

led = Pin(LORA_PINS.get('led', 25), Pin.OUT)

# OLED Display (optional)
display = None
try:
    i2c_rst = Pin(I2C_RST, Pin.OUT)
    i2c_rst.value(1)
    i2c = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
    
    if 0x3C in i2c.scan():
        import ssd1306
        display = ssd1306.SSD1306_I2C(128, 64, i2c)
        display.fill(0)
        display.text("LoRaWAN Sender", 0, 0)
        display.text(f"ID: {VEHICLE_ID}", 0, 16)
        display.show()
        print("OLED OK")
except:
    pass

# MPU6050
mpu_available = False
try:
    if 0x68 in i2c.scan():
        i2c.writeto_mem(0x68, 0x6B, b'\x00')
        mpu_available = True
        print("MPU6050 OK")
except:
    pass

def update_display(line1, line2="", line3="", line4=""):
    if not display:
        return
    display.fill(0)
    display.text(line1[:16], 0, 0)
    if line2: display.text(line2[:16], 0, 16)
    if line3: display.text(line3[:16], 0, 32)
    if line4: display.text(line4[:16], 0, 48)
    display.show()

# ===========================================
# LoRa INIT (Raw, für einfache Tests)
# Für echtes LoRaWAN: uLoRa oder lora-e5 Modul nutzen
# ===========================================
from sx127x import SX127x

spi = SPI(1, baudrate=5000000, polarity=0, phase=0,
          sck=Pin(LORA_PINS['sck']),
          mosi=Pin(LORA_PINS['mosi']),
          miso=Pin(LORA_PINS['miso']))

lora_params = {
    'frequency': LORA_FREQUENCY,
    'tx_power_level': LORA_TX_POWER,
    'signal_bandwidth': 125E3,
    'spreading_factor': LORA_SPREADING_FACTOR,
    'coding_rate': 5,
    'preamble_length': 8,
    'sync_word': 0x34,  # LoRaWAN Public: 0x34
    'enable_CRC': True,
}

lora = SX127x(spi, LORA_PINS, lora_params)
print(f"LoRa bereit auf {LORA_FREQUENCY/1E6:.1f} MHz")
update_display("LoRaWAN", f"{LORA_FREQUENCY/1E6:.1f}MHz", "Initialisiert")

# ===========================================
# PAYLOAD ENCODING (Cayenne LPP Format)
# TTN kann das automatisch dekodieren!
# ===========================================

def encode_state(fuel_percent, battery_v, state_code):
    """
    Enkodiert Fahrzeugstatus als Cayenne LPP
    
    Channel 1: Fuel (Analog Input, 0.01 resolution)
    Channel 2: Battery (Analog Input, 0.01 resolution)  
    Channel 3: State (Digital Input)
    """
    payload = bytearray()
    
    # Channel 1: Fuel (Type 0x02 = Analog Input)
    payload.append(0x01)  # Channel
    payload.append(0x02)  # Type: Analog Input
    fuel_int = int(fuel_percent * 100)  # 0.01 resolution
    payload.extend(struct.pack('>h', fuel_int))
    
    # Channel 2: Battery (Type 0x02 = Analog Input)
    payload.append(0x02)  # Channel
    payload.append(0x02)  # Type: Analog Input
    battery_int = int(battery_v * 100)
    payload.extend(struct.pack('>h', battery_int))
    
    # Channel 3: State (Type 0x00 = Digital Input)
    payload.append(0x03)  # Channel
    payload.append(0x00)  # Type: Digital Input
    payload.append(state_code & 0xFF)
    
    return bytes(payload)

def encode_gps(latitude, longitude, altitude=0):
    """
    Enkodiert GPS als Cayenne LPP
    Channel 4: GPS (Type 0x88)
    """
    payload = bytearray()
    
    # Channel 4: GPS (Type 0x88)
    payload.append(0x04)  # Channel
    payload.append(0x88)  # Type: GPS
    
    # Latitude: 0.0001° resolution, signed
    lat_int = int(latitude * 10000)
    payload.extend(struct.pack('>i', lat_int)[1:])  # 3 bytes
    
    # Longitude: 0.0001° resolution, signed
    lon_int = int(longitude * 10000)
    payload.extend(struct.pack('>i', lon_int)[1:])  # 3 bytes
    
    # Altitude: 0.01m resolution, signed
    alt_int = int(altitude * 100)
    payload.extend(struct.pack('>i', alt_int)[1:])  # 3 bytes
    
    return bytes(payload)

def encode_imu(acc_x, acc_y, acc_z):
    """
    Enkodiert IMU als Cayenne LPP
    Channel 5: Accelerometer (Type 0x71)
    """
    payload = bytearray()
    
    # Channel 5: Accelerometer (Type 0x71)
    payload.append(0x05)  # Channel
    payload.append(0x71)  # Type: Accelerometer
    
    # X, Y, Z in 0.001G resolution
    payload.extend(struct.pack('>h', int(acc_x * 1000)))
    payload.extend(struct.pack('>h', int(acc_y * 1000)))
    payload.extend(struct.pack('>h', int(acc_z * 1000)))
    
    return bytes(payload)

# ===========================================
# SENSOR FUNKTIONEN
# ===========================================
def read_mpu6050():
    if not mpu_available:
        return None
    try:
        raw = i2c.readfrom_mem(0x68, 0x3B, 6)
        ax, ay, az = [v / 16384.0 for v in ustruct.unpack('>hhh', raw)]
        return {'ax': ax, 'ay': ay, 'az': az}
    except:
        return None

def get_vehicle_state():
    """Simulierte Fahrzeugdaten - ersetze mit echten CAN-Daten"""
    import random
    
    fuel = 35.0 + random.uniform(-2, 2)
    battery = 12.8 + random.uniform(-0.3, 0.3)
    
    # State codes: 0=unknown, 1=parked, 2=idle, 3=driving
    imu = read_mpu6050()
    if imu:
        total_acc = (imu['ax']**2 + imu['ay']**2 + imu['az']**2)**0.5
        state_code = 3 if total_acc > 1.1 else 1
    else:
        state_code = 0
    
    return fuel, battery, state_code

def get_gps():
    """Simulierte GPS-Daten - ersetze mit echtem GPS-Modul"""
    import random
    lat = 49.2354 + random.uniform(-0.001, 0.001)  # Saarbrücken
    lon = 7.0000 + random.uniform(-0.001, 0.001)
    return lat, lon

# ===========================================
# HAUPTSCHLEIFE
# ===========================================
print("\nStarte LoRaWAN Sender...")
print(f"Sendeintervall: {SEND_INTERVAL_NORMAL}s")
print("Drücke Ctrl+C zum Beenden\n")

msg_count = 0
last_send = 0

try:
    while True:
        now = time.time()
        
        if now - last_send >= SEND_INTERVAL_NORMAL:
            # Daten sammeln
            fuel, battery, state = get_vehicle_state()
            lat, lon = get_gps()
            imu = read_mpu6050()
            
            # Payload erstellen (State + GPS)
            payload = encode_state(fuel, battery, state)
            payload += encode_gps(lat, lon)
            
            if imu:
                payload += encode_imu(imu['ax'], imu['ay'], imu['az'])
            
            # LED an
            led.value(1)
            
            # Senden
            print(f"[TX] Fuel={fuel:.1f}L Bat={battery:.2f}V State={state}")
            print(f"     GPS=({lat:.4f}, {lon:.4f})")
            print(f"     Payload: {payload.hex()} ({len(payload)} bytes)")
            
            if lora.send(payload):
                msg_count += 1
                print(f"     OK! (Total: {msg_count})")
                update_display(
                    "TX OK",
                    f"Fuel: {fuel:.1f}L",
                    f"Bat: {battery:.2f}V",
                    f"#{msg_count}"
                )
            else:
                print("     FEHLER!")
                update_display("TX FEHLER!", "", "", "")
            
            led.value(0)
            last_send = now
            gc.collect()
        
        time.sleep(1)

except KeyboardInterrupt:
    print(f"\n\nBeendet. {msg_count} Nachrichten gesendet.")
    lora.sleep()
