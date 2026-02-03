"""
SX127x LoRa Driver für MicroPython (Gateway Version)
Optimiert für kontinuierlichen Empfang
"""
from time import sleep
from machine import SPI, Pin
import gc

# Registers
REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_PA_CONFIG = 0x09
REG_LNA = 0x0c
REG_FIFO_ADDR_PTR = 0x0d
REG_FIFO_TX_BASE_ADDR = 0x0e
REG_FIFO_RX_BASE_ADDR = 0x0f
REG_FIFO_RX_CURRENT_ADDR = 0x10
REG_IRQ_FLAGS_MASK = 0x11
REG_IRQ_FLAGS = 0x12
REG_RX_NB_BYTES = 0x13
REG_PKT_RSSI_VALUE = 0x1a
REG_PKT_SNR_VALUE = 0x1b
REG_MODEM_CONFIG_1 = 0x1d
REG_MODEM_CONFIG_2 = 0x1e
REG_PREAMBLE_MSB = 0x20
REG_PREAMBLE_LSB = 0x21
REG_PAYLOAD_LENGTH = 0x22
REG_FIFO_RX_BYTE_ADDR = 0x25
REG_MODEM_CONFIG_3 = 0x26
REG_DETECTION_OPTIMIZE = 0x31
REG_DETECTION_THRESHOLD = 0x37
REG_SYNC_WORD = 0x39
REG_DIO_MAPPING_1 = 0x40
REG_VERSION = 0x42

# Modes
MODE_LONG_RANGE_MODE = 0x80
MODE_SLEEP = 0x00
MODE_STDBY = 0x01
MODE_TX = 0x03
MODE_RX_CONTINUOUS = 0x05

# IRQ masks
IRQ_TX_DONE_MASK = 0x08
IRQ_PAYLOAD_CRC_ERROR_MASK = 0x20
IRQ_RX_DONE_MASK = 0x40

FifoRxBaseAddr = 0x00


class SX127x:
    
    default_parameters = {
        'frequency': 868E6,
        'tx_power_level': 14,
        'signal_bandwidth': 125E3,
        'spreading_factor': 7,
        'coding_rate': 5,
        'preamble_length': 8,
        'sync_word': 0x34,
        'enable_CRC': True,
    }

    def __init__(self, spi, pins, parameters=None):
        self._spi = spi
        self._pins = pins
        self._parameters = parameters or self.default_parameters
        
        # Setup pins
        self._pin_ss = Pin(self._pins["ss"], Pin.OUT)
        self._pin_ss.value(1)
        
        if "reset" in self._pins:
            reset = Pin(self._pins["reset"], Pin.OUT)
            reset.value(0)
            sleep(0.01)
            reset.value(1)
            sleep(0.01)
        
        if "led" in self._pins:
            self._led = Pin(self._pins["led"], Pin.OUT)
        else:
            self._led = None
        
        if "dio_0" in self._pins:
            self._pin_dio0 = Pin(self._pins["dio_0"], Pin.IN)
        
        # Check version
        version = self._read_register(REG_VERSION)
        if version != 0x12:
            raise Exception(f'LoRa nicht gefunden (0x{version:02X})')
        
        print(f"SX127x OK (Version: 0x{version:02X})")
        
        # Initialize
        self.sleep()
        self._set_frequency(self._parameters['frequency'])
        self._set_signal_bandwidth(self._parameters['signal_bandwidth'])
        
        # LNA boost für besseren Empfang
        self._write_register(REG_LNA, self._read_register(REG_LNA) | 0x03)
        self._write_register(REG_MODEM_CONFIG_3, 0x04)
        
        self._set_spreading_factor(self._parameters['spreading_factor'])
        self._set_coding_rate(self._parameters['coding_rate'])
        self._set_preamble_length(self._parameters['preamble_length'])
        self._set_sync_word(self._parameters['sync_word'])
        self._enable_crc(self._parameters['enable_CRC'])
        
        self.standby()

    def _read_register(self, address):
        self._pin_ss.value(0)
        self._spi.write(bytes([address & 0x7F]))
        response = self._spi.read(1)
        self._pin_ss.value(1)
        return response[0]

    def _write_register(self, address, value):
        self._pin_ss.value(0)
        self._spi.write(bytes([address | 0x80, value]))
        self._pin_ss.value(1)

    def sleep(self):
        self._write_register(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_SLEEP)

    def standby(self):
        self._write_register(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STDBY)

    def _set_frequency(self, frequency):
        frf = int((frequency * (1 << 19)) / 32000000)
        self._write_register(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self._write_register(REG_FRF_MID, (frf >> 8) & 0xFF)
        self._write_register(REG_FRF_LSB, frf & 0xFF)

    def _set_signal_bandwidth(self, bandwidth):
        bw_map = {7800: 0, 10400: 1, 15600: 2, 20800: 3, 31250: 4,
                  41700: 5, 62500: 6, 125000: 7, 250000: 8, 500000: 9}
        bw = bw_map.get(int(bandwidth), 7)
        self._write_register(REG_MODEM_CONFIG_1, 
            (self._read_register(REG_MODEM_CONFIG_1) & 0x0F) | (bw << 4))

    def _set_spreading_factor(self, sf):
        sf = min(max(sf, 6), 12)
        if sf == 6:
            self._write_register(REG_DETECTION_OPTIMIZE, 0xC5)
            self._write_register(REG_DETECTION_THRESHOLD, 0x0C)
        else:
            self._write_register(REG_DETECTION_OPTIMIZE, 0xC3)
            self._write_register(REG_DETECTION_THRESHOLD, 0x0A)
        self._write_register(REG_MODEM_CONFIG_2,
            (self._read_register(REG_MODEM_CONFIG_2) & 0x0F) | ((sf << 4) & 0xF0))

    def _set_coding_rate(self, rate):
        rate = min(max(rate, 5), 8)
        self._write_register(REG_MODEM_CONFIG_1,
            (self._read_register(REG_MODEM_CONFIG_1) & 0xF1) | ((rate - 4) << 1))

    def _set_preamble_length(self, length):
        self._write_register(REG_PREAMBLE_MSB, (length >> 8) & 0xFF)
        self._write_register(REG_PREAMBLE_LSB, length & 0xFF)

    def _set_sync_word(self, word):
        self._write_register(REG_SYNC_WORD, word)

    def _enable_crc(self, enable):
        if enable:
            self._write_register(REG_MODEM_CONFIG_2,
                self._read_register(REG_MODEM_CONFIG_2) | 0x04)
        else:
            self._write_register(REG_MODEM_CONFIG_2,
                self._read_register(REG_MODEM_CONFIG_2) & 0xFB)

    def start_receive(self):
        """Startet kontinuierlichen Empfangsmodus"""
        self.standby()
        self._write_register(REG_FIFO_ADDR_PTR, FifoRxBaseAddr)
        self._write_register(REG_FIFO_RX_BASE_ADDR, FifoRxBaseAddr)
        self._write_register(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_RX_CONTINUOUS)
        
        if self._led:
            self._led.value(1)

    def check_receive(self):
        """
        Prüft ob Daten empfangen wurden (non-blocking).
        Gibt (payload, rssi, snr) zurück oder None.
        """
        irq = self._read_register(REG_IRQ_FLAGS)
        
        if not (irq & IRQ_RX_DONE_MASK):
            return None
        
        # LED blinken
        if self._led:
            self._led.value(0)
        
        # CRC Fehler?
        if irq & IRQ_PAYLOAD_CRC_ERROR_MASK:
            self._write_register(REG_IRQ_FLAGS, 0xFF)
            self.start_receive()
            return None
        
        # RSSI und SNR lesen
        rssi = self._read_register(REG_PKT_RSSI_VALUE) - 157
        snr = self._read_register(REG_PKT_SNR_VALUE) / 4
        
        # Daten lesen
        length = self._read_register(REG_RX_NB_BYTES)
        self._write_register(REG_FIFO_ADDR_PTR,
            self._read_register(REG_FIFO_RX_CURRENT_ADDR))
        
        data = bytes([self._read_register(REG_FIFO) for _ in range(length)])
        
        # IRQ löschen und Empfang neu starten
        self._write_register(REG_IRQ_FLAGS, 0xFF)
        self.start_receive()
        
        try:
            payload = data.decode('utf-8')
            return (payload, rssi, snr)
        except:
            return None

    def get_rssi(self):
        """Aktueller RSSI (Signalstärke)"""
        return self._read_register(REG_PKT_RSSI_VALUE) - 157
