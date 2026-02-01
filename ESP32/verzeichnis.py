import os, machine, sdcard
# Deine funktionierenden Pins
spi = machine.SoftSPI(baudrate=100000, sck=machine.Pin(14), mosi=machine.Pin(13), miso=machine.Pin(12))
sd = sdcard.SDCard(spi, machine.Pin(2))
try:
    os.mount(sd, "/sd")
    print("Mount erfolgreich!")
    print("Inhalt der SD-Karte:", os.listdir("/sd"))
except Exception as e:
    print("Fehler beim Mounten:", e)