"""
LoRa Sender Konfiguration für Smart-Car ESP32
"""
import ubinascii

# ===========================================
# FAHRZEUG-ID (eindeutig pro Fahrzeug)
# ===========================================
VEHICLE_ID = "FIESTA01"

# ===========================================
# LoRa Konfiguration (868 MHz für Europa)
# ===========================================
LORA_FREQUENCY = 868E6       # 868 MHz (EU)
LORA_TX_POWER = 14           # Sendeleistung (2-20 dBm)
LORA_SPREADING_FACTOR = 7    # 7-12 (höher = mehr Reichweite, langsamer)
LORA_BANDWIDTH = 125E3       # 125 kHz Standard
LORA_CODING_RATE = 5         # 5-8
LORA_SYNC_WORD = 0x34        # Privates Netzwerk (nicht 0x12 = LoRaWAN)

# ===========================================
# Pin-Mapping (Heltec WiFi LoRa 32 V2)
# Passe an dein Board an!
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

# Alternative: TTGO LoRa32
# LORA_PINS = {
#     'miso': 19,
#     'mosi': 27,
#     'ss': 18,
#     'sck': 5,
#     'dio_0': 26,
#     'reset': 23,
#     'led': 25
# }

# ===========================================
# I2C für MPU6050 (Beschleunigungssensor)
# ===========================================
I2C_SDA = 4
I2C_SCL = 15
I2C_RST = 16  # OLED Reset

# ===========================================
# CAN-Bus (MCP2515)
# ===========================================
CAN_CS = 17
CAN_CRYSTAL = 8000000  # 8 MHz Quarz
CAN_BITRATE = 500000   # 500 kbps (Standard für Autos)

# ===========================================
# SD-Karte (optional, für lokales Backup)
# ===========================================
SD_CS = 2
SD_SCK = 14
SD_MOSI = 13
SD_MISO = 12

# ===========================================
# Sende-Intervalle (Sekunden)
# ===========================================
SEND_INTERVAL_STATE = 10     # Status alle 10 Sekunden
SEND_INTERVAL_GPS = 30       # GPS alle 30 Sekunden
SEND_INTERVAL_IMU = 5        # IMU alle 5 Sekunden (nur bei Fahrt)
SEND_INTERVAL_ERROR = 1      # Fehler sofort senden

# ===========================================
# WLAN (optional, für NTP Zeitsync)
# ===========================================
WLAN_SSID = "MagentaWLAN-GUCJ"
WLAN_PASS = "36041308181537340217"
