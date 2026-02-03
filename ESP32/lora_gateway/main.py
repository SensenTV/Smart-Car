"""
Smart-Car LoRa Gateway
Empfängt LoRa-Daten von Fahrzeugen und leitet sie per MQTT weiter.

Hardware: ESP32 mit LoRa (Heltec/TTGO)

Datenfluss:
  ESP32 (Auto) --LoRa--> Gateway --WLAN/MQTT--> Mosquitto --> Node-RED --> InfluxDB
"""
import time
import gc
import network
from machine import Pin, SoftI2C, SPI

# Konfiguration laden
from config import (
    LORA_PINS, LORA_FREQUENCY, LORA_SPREADING_FACTOR, 
    LORA_BANDWIDTH, LORA_SYNC_WORD,
    I2C_SDA, I2C_SCL, I2C_RST,
    WLAN_SSID, WLAN_PASS,
    MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASS, 
    MQTT_CLIENT_ID, MQTT_TOPIC_PREFIX,
    GATEWAY_ID
)

# ===========================================
# STATISTIKEN
# ===========================================
stats = {
    'rx_count': 0,
    'mqtt_sent': 0,
    'mqtt_errors': 0,
    'crc_errors': 0,
    'last_rssi': 0,
    'last_snr': 0,
    'uptime': 0
}

# ===========================================
# HARDWARE INIT
# ===========================================
print("=" * 40)
print("Smart-Car LoRa Gateway")
print(f"Gateway ID: {GATEWAY_ID}")
print("=" * 40)

led = Pin(LORA_PINS.get('led', 25), Pin.OUT)
led.value(0)

# OLED Display (optional)
display = None
try:
    i2c_rst = Pin(I2C_RST, Pin.OUT)
    i2c_rst.value(1)
    i2c = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
    
    if 0x3C in i2c.scan():
        import ssd1306
        display = ssd1306.SSD1306_I2C(128, 64, i2c)
        print("OLED Display OK")
except Exception as e:
    print(f"OLED nicht verfuegbar: {e}")

def update_display(line1="", line2="", line3="", line4=""):
    """Aktualisiert Display"""
    if not display:
        return
    display.fill(0)
    display.text("LoRa Gateway", 0, 0)
    display.text("-" * 16, 0, 10)
    if line1: display.text(line1[:16], 0, 20)
    if line2: display.text(line2[:16], 0, 32)
    if line3: display.text(line3[:16], 0, 44)
    if line4: display.text(line4[:16], 0, 54)
    display.show()

update_display("Starte...", "", "", "")

# ===========================================
# WLAN VERBINDUNG
# ===========================================
print("\nVerbinde mit WLAN...")
update_display("WLAN...", WLAN_SSID[:16], "", "")

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WLAN_SSID, WLAN_PASS)

timeout = 20
while not wlan.isconnected() and timeout > 0:
    print(f"  Warte... ({timeout}s)")
    time.sleep(1)
    timeout -= 1

if wlan.isconnected():
    ip = wlan.ifconfig()[0]
    print(f"WLAN verbunden! IP: {ip}")
    update_display("WLAN OK", f"IP: {ip}", "", "")
else:
    print("WLAN FEHLER!")
    update_display("WLAN FEHLER!", "Neustart...", "", "")
    time.sleep(3)
    import machine
    machine.reset()

# ===========================================
# MQTT CLIENT
# ===========================================
print("\nVerbinde mit MQTT...")
from umqtt.simple import MQTTClient

mqtt = None

def connect_mqtt():
    global mqtt
    try:
        mqtt = MQTTClient(
            MQTT_CLIENT_ID,
            MQTT_BROKER,
            port=MQTT_PORT,
            user=MQTT_USER if MQTT_USER else None,
            password=MQTT_PASS if MQTT_PASS else None,
            keepalive=60
        )
        mqtt.connect()
        print(f"MQTT verbunden: {MQTT_BROKER}:{MQTT_PORT}")
        update_display("WLAN OK", f"MQTT: {MQTT_BROKER}", "", "")
        return True
    except Exception as e:
        print(f"MQTT Fehler: {e}")
        stats['mqtt_errors'] += 1
        return False

connect_mqtt()

def publish_mqtt(topic, payload):
    """Sendet Nachricht an MQTT Broker"""
    global mqtt
    try:
        if mqtt is None:
            connect_mqtt()
        mqtt.publish(topic, payload)
        stats['mqtt_sent'] += 1
        return True
    except Exception as e:
        print(f"MQTT Publish Fehler: {e}")
        stats['mqtt_errors'] += 1
        mqtt = None
        return False

# ===========================================
# LoRa INIT
# ===========================================
print("\nInitialisiere LoRa...")
from sx127x import SX127x

spi = SPI(1, baudrate=5000000, polarity=0, phase=0,
          sck=Pin(LORA_PINS['sck']),
          mosi=Pin(LORA_PINS['mosi']),
          miso=Pin(LORA_PINS['miso']))

lora_params = {
    'frequency': LORA_FREQUENCY,
    'signal_bandwidth': LORA_BANDWIDTH,
    'spreading_factor': LORA_SPREADING_FACTOR,
    'sync_word': LORA_SYNC_WORD,
    'enable_CRC': True,
}

lora = SX127x(spi, LORA_PINS, lora_params)
print(f"LoRa auf {LORA_FREQUENCY/1E6:.1f} MHz bereit!")

# Empfangsmodus starten
lora.start_receive()
print("\nWarte auf LoRa-Daten...")
update_display("Bereit!", f"Freq: {LORA_FREQUENCY/1E6:.0f}MHz", "Warte auf Daten", "")

# ===========================================
# NACHRICHTENVERARBEITUNG
# ===========================================
def process_message(payload, rssi, snr):
    """Verarbeitet empfangene LoRa-Nachricht"""
    stats['rx_count'] += 1
    stats['last_rssi'] = rssi
    stats['last_snr'] = snr
    
    print(f"\n[RX] {payload}")
    print(f"     RSSI: {rssi} dBm, SNR: {snr} dB")
    
    # Nachricht parsen: type,vehicle_id,...
    parts = payload.strip().split(',')
    if len(parts) < 2:
        print("     FEHLER: Ungültiges Format")
        return False
    
    msg_type = parts[0].lower()
    vehicle_id = parts[1]
    
    # MQTT Topic: smartcar/VEHICLE_ID
    topic = f"{MQTT_TOPIC_PREFIX}/{vehicle_id}"
    
    # An MQTT senden
    if publish_mqtt(topic, payload):
        print(f"     -> MQTT: {topic}")
        
        # Display aktualisieren
        update_display(
            f"RX: {msg_type}",
            f"Von: {vehicle_id}",
            f"RSSI: {rssi}dBm",
            f"Gesamt: {stats['rx_count']}"
        )
        return True
    else:
        print("     MQTT FEHLER!")
        return False

# ===========================================
# STATUS PUBLISHING
# ===========================================
def publish_gateway_status():
    """Sendet Gateway-Status an MQTT"""
    import json
    status = {
        'gateway_id': GATEWAY_ID,
        'uptime_s': stats['uptime'],
        'rx_count': stats['rx_count'],
        'mqtt_sent': stats['mqtt_sent'],
        'mqtt_errors': stats['mqtt_errors'],
        'last_rssi': stats['last_rssi'],
        'last_snr': stats['last_snr'],
        'free_mem_kb': gc.mem_free() // 1024,
        'wlan_rssi': wlan.status('rssi') if wlan.isconnected() else 0
    }
    topic = f"{MQTT_TOPIC_PREFIX}/gateway/{GATEWAY_ID}/status"
    publish_mqtt(topic, json.dumps(status))

# ===========================================
# HAUPTSCHLEIFE
# ===========================================
print("\n" + "=" * 40)
print("Gateway läuft - warte auf LoRa-Pakete")
print("Drücke Ctrl+C zum Beenden")
print("=" * 40 + "\n")

start_time = time.time()
last_status = 0
last_wlan_check = 0

try:
    while True:
        now = time.time()
        stats['uptime'] = int(now - start_time)
        
        # LoRa Empfang prüfen (non-blocking)
        result = lora.check_receive()
        if result:
            payload, rssi, snr = result
            process_message(payload, rssi, snr)
            led.value(1)
            time.sleep(0.05)
            led.value(0)
        
        # WLAN prüfen (alle 30 Sekunden)
        if now - last_wlan_check >= 30:
            if not wlan.isconnected():
                print("WLAN verloren - reconnect...")
                wlan.connect(WLAN_SSID, WLAN_PASS)
                time.sleep(5)
            last_wlan_check = now
        
        # Gateway Status senden (alle 60 Sekunden)
        if now - last_status >= 60:
            publish_gateway_status()
            last_status = now
            gc.collect()
        
        # Kurze Pause um CPU zu entlasten
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n\nGateway beendet.")
    print(f"Statistik:")
    print(f"  Empfangen: {stats['rx_count']}")
    print(f"  MQTT gesendet: {stats['mqtt_sent']}")
    print(f"  MQTT Fehler: {stats['mqtt_errors']}")
    lora.sleep()
    wlan.active(False)
