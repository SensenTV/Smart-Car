import network
import ntptime
from machine import Pin, SoftI2C, SoftSPI, RTC
import oled as ssd1306
import sdcard
import os
import time
import ustruct
from mcp2515 import MCP2515, CANFrame

# --- WLAN ZUGANGSDATEN ---
WLAN_SSID = "MagentaWLAN-GUCJ"
WLAN_PASS = "36041308181537340217"

# --- KONFIGURATION PINS ---
I2C_SDA, I2C_SCL, I2C_RST = 4, 15, 16 
SD_CS, SD_SCK, SD_MOSI, SD_MISO = 2, 14, 13, 12 
CAN_CS = 17 

# --- INITIALISIERUNG HARDWARE ---
reset = Pin(I2C_RST, Pin.OUT)
reset.value(1)
i2c = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

try:
    i2c.writeto_mem(0x68, 0x6B, b'\x00') # MPU wecken
except:
    print("MPU6050 nicht gefunden")

# --- FUNKTION: ZEIT SYNC ---
def sync_time():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    display.fill(0)
    display.text("WiFi Connect...", 0, 0)
    display.show()
    wlan.connect(WLAN_SSID, WLAN_PASS)
    
    versuche = 0
    while not wlan.isconnected() and versuche < 10:
        time.sleep(1)
        versuche += 1
    
    if wlan.isconnected():
        try:
            ntptime.settime()
            rtc = RTC()
            t = list(rtc.datetime())
            t[4] = (t[4] + 1) % 24 # +1h Winterzeit
            rtc.datetime(tuple(t))
            display.text("Time OK", 0, 15)
        except:
            display.text("NTP Error", 0, 15)
    else:
        display.text("WiFi Failed", 0, 15)
    display.show()
    wlan.active(False)

sync_time()

# --- SPI BUS INITIALISIERUNG ---
spi = SoftSPI(baudrate=1000000, sck=Pin(SD_SCK), mosi=Pin(SD_MOSI), miso=Pin(SD_MISO))

# --- SD INITIALISIERUNG ---
sd_ready = False
filename = "/default_log.csv"
try:
    sd = sdcard.SDCard(spi, Pin(SD_CS))
    os.mount(sd, "/sd")
    sd_ready = True
    t = time.localtime()
    filename = "/sd/{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}.csv".format(t[0], t[1], t[2], t[3], t[4], t[5])
    with open(filename, "w") as f:
        f.write("Uptime_ms,AccX,AccY,AccZ,CAN_ID,CAN_Data\n")
    print("Logge in:", filename)
except Exception as e:
    print("SD Fehler:", e)

# --- CAN INITIALISIERUNG ---
can_ready = False
try:
    # ACHTUNG: crystal=8000000 (8MHz) oder 16000000 (16MHz)
    can = MCP2515(spi, Pin(CAN_CS), crystal=8000000)
    can.reset()
    can.set_bitrate(500000)
    can.set_mode(0)
    can_ready = True
    print("CAN bereit!")
except Exception as e:
    print("CAN Fehler:", e)

# --- HAUPTSCHLEIFE ---
start_tick = time.ticks_ms()

while True:
    try:
        # A) MPU6050 Daten
        raw = i2c.readfrom_mem(0x68, 0x3B, 6)
        ax, ay, az = [v / 16384.0 for v in ustruct.unpack('>hhh', raw)]
        uptime = time.ticks_diff(time.ticks_ms(), start_tick)
        
        # B) CAN Daten
        c_id, c_data = "None", "None"
        if can_ready:
            msg = can.read_message()
            if msg:
                c_id = "0x{:03X}".format(msg.arbitration_id)
                c_data = "-".join(["%02X" % b for b in msg.data])

        # C) Display
        display.fill(0)
        display.text("REC: " + filename[-15:], 0, 0)
        display.text("ID: " + c_id, 0, 15)
        display.text("X:{:.2f} Y:{:.2f}".format(ax, ay), 0, 35)
        display.text("Z:{:.2f}g".format(az), 0, 45)
        display.show()
        
        # D) SD Speichern
        if sd_ready:
            log_str = "{},{:.2f},{:.2f},{:.2f},{},{}\n".format(uptime, ax, ay, az, c_id, c_data)
            with open(filename, "a") as f:
                f.write(log_str)
            # os.sync() # Nur nutzen wenn die SD sehr langsam ist

    except KeyboardInterrupt:
        print("Stoppe Logger...")
        break
    except Exception as e:
        print("Fehler im Loop:", e)
        
    time.sleep(0.1)