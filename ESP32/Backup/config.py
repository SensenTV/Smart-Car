import ubinascii

# Diese Keys findest du in deiner TTN Console
# WICHTIG: In MicroPython kopierst du sie meist als HEX-String (MSB)
DEV_EUI = ubinascii.unhexlify('70B3D57ED00754DB')
JOIN_EUI = ubinascii.unhexlify('0000000000000000') # Früher AppEUI
APP_KEY = ubinascii.unhexlify('63E84F820D9F1C5C03746C31C285F651')

# Pin-Mapping für die meisten ESP32 LoRa Boards (Heltec/TTGO)
LORA_PINS = {
    'miso': 19,
    'mosi': 27,
    'ss': 18,
    'sck': 5,
    'dio_0': 26,
    'reset': 14,
    'led': 25 
}