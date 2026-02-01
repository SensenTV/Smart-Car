from machine import Pin
import time

# MCP2515 Register Adressen
CANSTAT = 0x0E
CANCTRL = 0x0F
TEC     = 0x1C
REC     = 0x1D
CNF3    = 0x28
CNF2    = 0x29
CNF1    = 0x2A
CANINTF = 0x2C
TXB0CTRL = 0x30
TXB0SIDH = 0x31
RXB0CTRL = 0x60
RXB0SIDH = 0x61

class CANFrame:
    def __init__(self, can_id, data):
        self.arbitration_id = can_id
        self.data = data
    def __repr__(self):
        return "ID: 0x{:x} Data: {}".format(self.arbitration_id, list(self.data))

class MCP2515:
    def __init__(self, spi, cs, crystal=8000000):
        self.spi = spi
        self.cs = cs
        self.crystal = crystal
        self.cs.value(1)

    def _write(self, addr, val):
        self.cs.value(0)
        self.spi.write(bytearray([0x02, addr, val]))
        self.cs.value(1)

    def _read(self, addr):
        self.cs.value(0)
        self.spi.write(bytearray([0x03, addr]))
        val = self.spi.read(1)
        self.cs.value(1)
        return val[0]

    def reset(self):
        self.cs.value(0)
        self.spi.write(bytearray([0xC0])) # Reset Kommando
        self.cs.value(1)
        time.sleep(0.01)

    def set_bitrate(self, bitrate):
        # Vereinfachte Berechnung für 500kbps bei 8MHz Quarz
        if self.crystal == 8000000 and bitrate == 500000:
            self._write(CNF1, 0x00) # Brp = 0
            self._write(CNF2, 0x90) # Phase 1
            self._write(CNF3, 0x02) # Phase 2
        # Für 16MHz Quarz (falls vorhanden)
        elif self.crystal == 16000000 and bitrate == 500000:
            self._write(CNF1, 0x00)
            self._write(CNF2, 0xD1)
            self._write(CNF3, 0x01)

    def set_mode(self, mode):
        # 0 = Normal, 4 = Configuration, 3 = Listen Only
        self._write(CANCTRL, mode << 5)

    def send_message(self, frame):
        # Sendet über Buffer 0
        self._write(TXB0SIDH, (frame.arbitration_id >> 3) & 0xFF)
        self._write(0x32, (frame.arbitration_id << 5) & 0xE0) # SIDL
        self._write(0x35, len(frame.data)) # DLC
        for i, b in enumerate(frame.data):
            self._write(0x36 + i, b)
        self.cs.value(0)
        self.spi.write(bytearray([0x81])) # Request to Send TXB0
        self.cs.value(1)

    def read_message(self):
        # Prüfen ob Nachricht in RXB0
        if not (self._read(CANINTF) & 0x01):
            return None
        
        id_h = self._read(RXB0SIDH)
        id_l = self._read(0x62)
        can_id = (id_h << 3) | (id_l >> 5)
        dlc = self._read(0x65) & 0x0F
        data = bytearray()
        for i in range(dlc):
            data.append(self._read(0x66 + i))
        
        self._write(CANINTF, 0x00) # Flag löschen
        return CANFrame(can_id, data)
