"""
LoRa Gateway Konfiguration
Empfängt LoRa-Daten und leitet sie an MQTT weiter.
"""

# ===========================================
# LoRa Konfiguration (MUSS mit Sender übereinstimmen!)
# ===========================================
LORA_FREQUENCY = 868E6       # 868 MHz (EU)
LORA_SPREADING_FACTOR = 7    # Muss mit Sender übereinstimmen
LORA_BANDWIDTH = 125E3       # Muss mit Sender übereinstimmen
LORA_SYNC_WORD = 0x34        # Muss mit Sender übereinstimmen

# ===========================================
# Pin-Mapping (Heltec WiFi LoRa 32 V2)
# ===========================================
LORA_PINS = {
    'miso': 19,
    'mosi': 27,
    'ss': 18,
    'sck': 5,
    'dio_0': 26,
    'reset': 14,
    'led': 25
}

# ===========================================
# I2C für OLED Display
# ===========================================
I2C_SDA = 4
I2C_SCL = 15
I2C_RST = 16

# ===========================================
# WLAN für MQTT
# ===========================================
WLAN_SSID = "MagentaWLAN-GUCJ"
WLAN_PASS = "36041308181537340217"

# ===========================================
# MQTT Broker
# ===========================================
MQTT_BROKER = "192.168.2.100"  # IP des Docker-Hosts mit Mosquitto
MQTT_PORT = 1883
MQTT_USER = ""                  # Leer wenn keine Auth
MQTT_PASS = ""
MQTT_CLIENT_ID = "lora-gateway"
MQTT_TOPIC_PREFIX = "smartcar"  # Ergibt z.B. "smartcar/FIESTA01"

# ===========================================
# Gateway Einstellungen
# ===========================================
GATEWAY_ID = "GW01"
DISPLAY_TIMEOUT = 10  # Sekunden bis Display dunkel wird
