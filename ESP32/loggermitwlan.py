import network
import ntptime
from machine import Pin, SoftI2C, SoftSPI, RTC
import oled as ssd1306
import sdcard
import os
import time
import ustruct

# --- WLAN ZUGANGSDATEN ---
WLAN_SSID = "MagentaWLAN-GUCJ"
WLAN_PASS = "36041308181537340217"

# --- KONFIGURATION PINS ---
I2C_SDA, I2C_SCL, I2C_RST = 4, 15, 16 #pins für gyro
SD_CS, SD_SCK, SD_MOSI, SD_MISO = 2, 14, 13, 12 #pins für sd

# --- INITIALISIERUNG HARDWARE ---
reset = Pin(I2C_RST, Pin.OUT); reset.value(1)
i2c = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
display = ssd1306.SSD1306_I2C(128, 64, i2c)
i2c.writeto_mem(0x68, 0x6B, b'\x00') # MPU wecken

# --- FUNKTION: ZEIT ÜBER WLAN HOLEN ---
def sync_time():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    display.fill(0)
    display.text("WiFi Connect...", 0, 0)
    display.show()
    
    wlan.connect(WLAN_SSID, WLAN_PASS)
    
    # Warten auf Verbindung (max 10 Sek)
    versuche = 0
    while not wlan.isconnected() and versuche < 10:
        time.sleep(1)
        versuche += 1
        print("Verbinde...")
    
    if wlan.isconnected():
        print("WLAN verbunden!")
        display.text("WiFi OK", 0, 15)
        display.show()
        
        try:
            ntptime.settime() # Holt UTC Zeit vom Server
            print("Zeit synchronisiert.")
            # HINWEIS: ntptime gibt UTC. Für Deutschland (MEZ) +1 oder (MESZ) +2 Stunden.
            # Hier ein einfacher Offset von +1 Stunde (Winterzeit):
            rtc = RTC()
            current_time = rtc.datetime()
            # rtc.datetime format: (Y, M, D, WD, H, M, S, SubS)
            new_time = list(current_time)
            new_time[4] = (new_time[4] + 1) % 24 # +1 Stunde für Deutschland
            rtc.datetime(tuple(new_time))
            
        except:
            print("NTP Fehler.")
    else:
        print("WLAN fehlgeschlagen.")
    
    wlan.active(False) # WLAN wieder aus, um Strom zu sparen

# 1. Zeit synchronisieren
sync_time()

# 2. SD-Karte vorbereiten
spi = SoftSPI(baudrate=100000, sck=Pin(SD_SCK), mosi=Pin(SD_MOSI), miso=Pin(SD_MISO))
sd_ready = False
filename = ""

try:
    sd = sdcard.SDCard(spi, Pin(SD_CS))
    vfs = os.VfsFat(sd)
    os.mount(vfs, "/sd")
    sd_ready = True
    
    # Dateinamen generieren (jetzt mit echter Zeit)
    t = time.localtime()
    filename = "/sd/{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}.csv".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )
    
    with open(filename, "w") as f:
        f.write("Zeit_ms,AccX,AccY,AccZ\n")
    os.sync()
    print("Logge in:", filename)

except Exception as e:
    print("SD Fehler:", e)

# 3. Hauptschleife
start_tick = time.ticks_ms()
while True:
    try:
        raw = i2c.readfrom_mem(0x68, 0x3B, 6)
        ax, ay, az = [v / 16384.0 for v in ustruct.unpack('>hhh', raw)]
        uptime = time.ticks_diff(time.ticks_ms(), start_tick)
        
        display.fill(0)
        display.text("LOGGING REALTIME", 0, 0)
        display.text("File: " + filename[4:], 0, 15)
        display.text("X: {:.2f}g".format(ax), 0, 35)
        display.text("Y: {:.2f}g".format(ay), 0, 45)
        display.text("Z: {:.2f}g".format(az), 0, 55)
        display.show()
        
        if sd_ready:
            with open(filename, "a") as f:
                f.write("{},{:.2f},{:.2f},{:.2f}\n".format(uptime, ax, ay, az))
            os.sync() 

    except KeyboardInterrupt:
        break
    time.sleep(1)