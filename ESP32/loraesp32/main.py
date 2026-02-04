import machine
import time
import network
import socket
import random
import os

# --- KONFIGURATION ---
WIFI_SSID = "Tim Wall"
WIFI_PASS = "12345678"
PC_IP = "10.167.19.7"   
PC_PORT = 8080
LOG_FILE = "passat_b5_log.csv"

# Optional: UDP
UDP_IP = PC_IP
UDP_PORT = 5005 
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- SIMULATION KLASSE (VW Passat B5 Profil) ---
class PassatSimulator:
    def __init__(self):
        self.vehicle_id = "VW-Passat-B5-TDI"
        
        # Fahrzeug Zustand
        self.engine_running = False 
        self.is_cranking = False # Anlasser dreht
        self.current_state = "parked" 
        
        # Werte
        self.rpm = 0
        self.speed = 0
        self.fuel = 62.0  # Passat B5 hat ca. 62L Tank
        self.start_fuel = 62.0
        self.voltage = 12.6 # Gute Batterie
        self.coolant_temp = 20.0 # Start bei Umgebungstemperatur
        self.gear = 0
        self.odometer = 215400.0 # Realistischer KM-Stand
        
        # Physik-Parameter (Übersetzung Speed km/h pro 1000 RPM)
        # Bsp: 5. Gang bei 2000 RPM = ca 100 km/h
        self.gear_ratios = {0: 0, 1: 8.5, 2: 15.2, 3: 24.8, 4: 35.1, 5: 48.5}
        
        # Trip
        self.trip_id = ""
        self.trip_start_time = 0
        self.trip_duration = 0

    def start_sequence(self):
        """Startet den Anlasser-Prozess"""
        print("🔑 Schlüssel gedreht -> Anlasser orgelt...")
        self.is_cranking = True
        self.current_state = "cranking"
        # Spannungseinbruch beim Starten simulieren
        self.voltage = 10.5 
        self.rpm = 250 # Anlasser Drehzahl

    def engine_fired(self):
        """Motor springt an"""
        print("💨 Motor läuft!")
        self.is_cranking = False
        self.engine_running = True
        self.current_state = "idling"
        self.rpm = 900 # Kaltleerlauf etwas höher
        self.voltage = 14.2 # Lichtmaschine lädt
        
        # Trip initialisieren
        self.trip_id = "TRIP_" + str(random.randint(10000, 99999))
        self.trip_start_time = time.time()
        self.start_fuel = self.fuel

    def update(self):
        # 1. PARKED
        if not self.engine_running and not self.is_cranking:
            self.rpm = 0
            self.speed = 0
            self.voltage = 12.5 + random.uniform(-0.02, 0.02)
            self.current_state = "parked"
            return 

        # 2. CRANKING (Startvorgang dauert kurz)
        if self.is_cranking:
            if random.random() > 0.8: # 20% Chance pro Tick dass er anspringt
                self.engine_fired()
            return

        # --- MOTOR LÄUFT AB HIER ---
        self.trip_duration = time.time() - self.trip_start_time

        # Simulation eines Fahrprofils (Beschleunigen auf 50 km/h)
        target_speed = 50 # km/h Ziel
        
        # Drehzahl/Gang Logik
        if self.gear == 0: self.gear = 1
        
        # Automatisches "Schalten" für Simulation
        current_ratio = self.gear_ratios[self.gear]
        
        # Wenn wir fahren, berechnet sich RPM aus Speed und Gang
        # Wenn wir stehen (Ampel), ist RPM Leerlauf
        
        # Einfache Physik: Beschleunigung
        if self.speed < target_speed:
            self.speed += 2.5 # Beschleunigen
        else:
            self.speed += random.uniform(-1, 1) # Geschwindigkeit halten

        # Schalten (Hochschalten bei 2800 RPM)
        if self.rpm > 2800 and self.gear < 5:
            self.gear += 1
            self.rpm -= 800 # Drehzahl fällt beim Schalten
        
        # RPM aus Speed berechnen (Rückwärtsrechnung)
        if self.gear > 0:
            calc_rpm = (self.speed / self.gear_ratios[self.gear]) * 1000
            # RPM darf nicht unter Leerlauf fallen
            self.rpm = max(900, int(calc_rpm))
            
            # Im Leerlauf an der Ampel auskuppeln simulieren
            if self.speed < 2: 
                self.rpm = 900
                self.speed = 0

        # Status Update
        self.current_state = "driving" if self.speed > 0 else "idling"

        # Temperatur Simulation (Warmfahren)
        if self.coolant_temp < 90.0:
            self.coolant_temp += 0.5 + (self.rpm / 5000)

        # Verbrauch (Liter pro Stunde Logik grob angenähert)
        # Leerlauf: 0.8 L/h, Fahren: Lastabhängig
        liter_per_sec = (0.8 / 3600) if self.speed == 0 else (6.5 / 100 / 3600 * self.speed)
        self.fuel -= liter_per_sec
        
        # Spannung (Lichtmaschine regelt)
        self.voltage = 14.3 + random.uniform(-0.1, 0.1)
        
        # Kilometerzähler
        km_driven_this_tick = (self.speed / 3600) * 0.1 # bei 0.1s Takt
        self.odometer += km_driven_this_tick


# --- HILFSFUNKTIONEN ---

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f'Verbinde mit WLAN {WIFI_SSID}...')
        try:
            wlan.connect(WIFI_SSID, WIFI_PASS)
        except OSError: pass
        timeout = 0
        while not wlan.isconnected():
            time.sleep(1)
            timeout += 1
            if timeout > 10:
                print("❌ WLAN Fehler! Simulation läuft offline.")
                return False
    print('✅ WLAN verbunden:', wlan.ifconfig())
    return True

def send_file_to_pc():
    print(f"--- SENDE LOG DATEI ---")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3) 
    try:
        s.connect((PC_IP, PC_PORT))
        with open(LOG_FILE, 'r') as f:
            while True:
                chunk = f.read(1024)
                if not chunk: break
                s.send(chunk.encode('utf-8'))
        print("✅ Log erfolgreich hochgeladen!")
    except Exception as e:
        print(f"⚠️ Upload nicht möglich (Server nicht an?): {e}")
    finally:
        s.close()

# --- HAUPTPROGRAMM ---

def main():
    print("--- BOOT PASSAT ECU ---")
    wifi_connected = connect_wifi()
    
    car = PassatSimulator()
    
    # Simulations-Dauer (z.B. 15 Sekunden Fahrt)
    duration = 15 
    start_time = time.time()
    tick = 0
    
    print(f"Starte Datenerfassung ({duration}s)...")
    
    # Datei Header schreiben
    with open(LOG_FILE, 'w') as f:
        # Header Zeile für CSV (optional, aber gut für Excel)
        f.write("type,vehicle_id,timestamp,val1,val2,val3,val4\n")
        
        while time.time() - start_time < duration:
            tick += 1
            
            # LOGIK: Nach 2 Sek Zündung, nach 3 Sek Motor an
            if not car.engine_running and not car.is_cranking:
                if (time.time() - start_time) > 1.5:
                    car.start_sequence()
            
            car.update()
            
            # --- DATEN PAKETE ---
            # Wir trennen jetzt Telemetrie (schnell) und Status (langsam)
            
            ts = int(time.time())
            
            # 1. Telemetrie (Live Motordaten)
            # Format: telem, ID, RPM, Speed, Temp, Gear
            line_telem = f"telem,{car.vehicle_id},{ts},{car.rpm},{int(car.speed)},{int(car.coolant_temp)},{car.gear}\n"
            f.write(line_telem)
            
            # 2. Status (Batterie, Tank, ODO) - seltener, z.B. alle 10 Ticks
            if tick % 10 == 0:
                # Format: status, ID, State, Fuel, Voltage, ODO
                line_status = f"status,{car.vehicle_id},{ts},{car.current_state},{car.fuel:.3f},{car.voltage:.2f},{car.odometer:.1f}\n"
                f.write(line_status)
            
            # 3. UDP Live Stream (falls WLAN da)
            if wifi_connected:
                try:
                    udp_sock.sendto(line_telem.encode(), (UDP_IP, UDP_PORT))
                except: pass

            # Console Output zur Kontrolle
            if tick % 5 == 0:
                print(f"[{car.current_state.upper()}] {car.rpm} U/min | {int(car.speed)} km/h | {car.coolant_temp:.1f}°C")
            
            time.sleep(0.1) # 10Hz Abtastrate

    print("Fahrt beendet.")
    if wifi_connected:
        send_file_to_pc()
    print("--- SYSTEM HALT ---")

if __name__ == "__main__":
    main()
