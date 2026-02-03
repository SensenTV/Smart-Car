"""
LoRaWAN Konfiguration für Smart-Car ESP32
Für The Things Network (TTN) oder ChirpStack

WICHTIG: Die Keys bekommst du aus der TTN Console!
https://console.cloud.thethings.network/
"""

# ===========================================
# FAHRZEUG-ID
# ===========================================
VEHICLE_ID = "FIESTA01"

# ===========================================
# TTN/LoRaWAN OTAA Keys
# Diese findest du in der TTN Console unter:
# Applications -> Deine App -> End devices -> Dein Device
# ===========================================

# Device EUI (LSB Format) - 8 Bytes
# In TTN Console: "DevEUI" kopieren
DEV_EUI = '70B3D57ED00754DB'

# Join EUI / App EUI (LSB Format) - 8 Bytes  
# In TTN Console: "JoinEUI" oder "AppEUI"
JOIN_EUI = '0000000000000000'

# App Key (MSB Format) - 16 Bytes
# In TTN Console: "AppKey" -> "Toggle array formatting" auf MSB
APP_KEY = '63E84F820D9F1C5C03746C31C285F651'

# ===========================================
# LoRaWAN Einstellungen (EU868)
# ===========================================
LORA_FREQUENCY = 868100000   # EU868 Kanal 1
LORA_SPREADING_FACTOR = 7    # SF7-SF12 (7 = schnell, 12 = weit)
LORA_BANDWIDTH = 125000      # 125 kHz
LORA_TX_POWER = 14           # dBm (max 14 für EU)
LORA_CODING_RATE = 5         # 4/5

# EU868 Frequenzplan (TTN nutzt diese)
EU868_FREQUENCIES = [
    868100000,  # Kanal 0
    868300000,  # Kanal 1
    868500000,  # Kanal 2
    867100000,  # Kanal 3
    867300000,  # Kanal 4
    867500000,  # Kanal 5
    867700000,  # Kanal 6
    867900000,  # Kanal 7
]

# ===========================================
# Pin-Mapping (Heltec WiFi LoRa 32 V2)
# ===========================================
LORA_PINS = {
    'miso': 19,
    'mosi': 27,
    'ss': 18,
    'sck': 5,
    'dio_0': 26,
    'dio_1': 35,  # Wichtig für LoRaWAN!
    'reset': 14,
    'led': 25
}

# Alternative: TTGO LoRa32 V2.1
# LORA_PINS = {
#     'miso': 19,
#     'mosi': 27,
#     'ss': 18,
#     'sck': 5,
#     'dio_0': 26,
#     'dio_1': 33,
#     'reset': 23,
#     'led': 25
# }

# ===========================================
# I2C für Sensoren
# ===========================================
I2C_SDA = 4
I2C_SCL = 15
I2C_RST = 16

# ===========================================
# Sende-Intervalle (Sekunden)
# ACHTUNG: TTN Fair Use Policy = max 30s Airtime/Tag
# Bei SF7 ca. 50ms pro Nachricht = max ~600 Nachrichten/Tag
# ===========================================
SEND_INTERVAL_NORMAL = 60    # Alle 60 Sekunden im Normalbetrieb
SEND_INTERVAL_DRIVING = 30   # Alle 30 Sekunden während Fahrt
SEND_INTERVAL_ALERT = 10     # Alle 10 Sekunden bei Alarm

# ===========================================
# Payload Ports (für TTN Decoder)
# ===========================================
PORT_STATE = 1      # Fahrzeugstatus
PORT_GPS = 2        # GPS Koordinaten
PORT_IMU = 3        # Beschleunigung
PORT_ERROR = 4      # Fehlercodes
PORT_ALERT = 5      # Alarme
