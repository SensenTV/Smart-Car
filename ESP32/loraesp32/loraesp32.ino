/*
 * ESP32 LoRa Sender fÃ¼r Smart-Car Dashboard
 * 
 * Payload Format (4 Bytes):
 * - Byte 0: Vehicle ID (1=Ford_Siesta)
 * - Byte 1: Message Type (1=Status, 2=Trip End, 3=Error, 4=Idle)
 * - Byte 2: Wert 1 (je nach Type)
 * - Byte 3: Wert 2 (je nach Type)
 * 
 * Type 1 (STATUS):   [ID, 1, Fuel_L, Battery*10]
 * Type 2 (TRIP_END): [ID, 2, Duration_min, FuelUsed*10]
 * Type 3 (ERROR):    [ID, 3, ErrorCode, Battery*10]
 * Type 4 (IDLE):     [ID, 4, Fuel_L, Battery*10]
 */

#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>

// --- FAHRZEUG KONFIGURATION ---
#define VEHICLE_FORD_SIESTA  1
const uint8_t CURRENT_VEHICLE = VEHICLE_FORD_SIESTA;

// Nachrichten-Typen (passend zu Python Receiver)
#define TYPE_STATUS    1  // Fahrend
#define TYPE_TRIP_END  2  // Fahrt beendet
#define TYPE_ERROR     3  // Fehler
#define TYPE_IDLE      4  // Steht

// Error Codes (passend zu Python Receiver)
#define ERR_OK            0
#define ERR_BATTERY_LOW   1
#define ERR_CHECK_ENGINE  2
#define ERR_LOW_OIL       3
#define ERR_TIRE_PRESSURE 4

// --- LORAWAN KEYS ---
static const u1_t PROGMEM APPEUI[8] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
void os_getArtEui (u1_t* buf) { memcpy_P(buf, APPEUI, 8); }

static const u1_t PROGMEM DEVEUI[8] = { 0x78, 0x58, 0x07, 0xD0, 0x7E, 0xD5, 0xB3, 0x70 }; // LSB!
void os_getDevEui (u1_t* buf) { memcpy_P(buf, DEVEUI, 8); }

static const u1_t PROGMEM APPKEY[16] = { 0x98, 0x5B, 0x7D, 0x43, 0x82, 0x33, 0x10, 0x24, 0xFC, 0x61, 0xA5, 0xAB, 0x86, 0xCC, 0x8B, 0xD3 }; // MSB
void os_getDevKey (u1_t* buf) { memcpy_P(buf, APPKEY, 16); }

// --- PAYLOAD (4 Bytes) ---
uint8_t payload[4];
static osjob_t sendjob;

// Simulierte Fahrzeugdaten (ersetze durch echte Sensoren)
uint8_t currentFuel = 45;      // Aktueller Tankstand
float currentBattery = 12.8;   // Batteriespannung
bool tripActive = false;       // Fahrt aktiv?
unsigned long tripStartTime;   // Fahrt-Startzeit
uint8_t tripStartFuel;         // Tank bei Fahrtstart

// --- PAYLOAD ERSTELLEN ---
void sendStatus() {
    payload[0] = CURRENT_VEHICLE;
    payload[1] = TYPE_STATUS;
    payload[2] = currentFuel;
    payload[3] = (uint8_t)(currentBattery * 10);
    Serial.println(F("Sende: STATUS (Driving)"));
}

void sendTripEnd(uint8_t durationMin, float fuelUsed) {
    payload[0] = CURRENT_VEHICLE;
    payload[1] = TYPE_TRIP_END;
    payload[2] = durationMin;
    payload[3] = (uint8_t)(fuelUsed * 10);  // x10 fuer Dezimalstellen
    Serial.print(F("Sende: TRIP END | Dauer: "));
    Serial.print(durationMin);
    Serial.print(F("min | Verbrauch: "));
    Serial.print(fuelUsed);
    Serial.println(F("L"));
}

void sendError(uint8_t errorCode) {
    payload[0] = CURRENT_VEHICLE;
    payload[1] = TYPE_ERROR;
    payload[2] = errorCode;
    payload[3] = (uint8_t)(currentBattery * 10);
    Serial.print(F("Sende: ERROR Code "));
    Serial.println(errorCode);
}

void sendIdle() {
    payload[0] = CURRENT_VEHICLE;
    payload[1] = TYPE_IDLE;
    payload[2] = currentFuel;
    payload[3] = (uint8_t)(currentBattery * 10);
    Serial.println(F("Sende: IDLE (Parked)"));
}

// --- DEMO: Zufaellige Nachrichten ---
// --- DEMO: Zufaellige Nachrichten ---
void preparePayload() {
    // Erzeugt eine Zahl von 0 bis 99
    int chance = random(0, 100); 
    int chance0 = 0;
    
    if (chance < 99) {
        // 0 - 49 (50%) -> Status (Fahrend)
        
        uint8_t duration = random(10, 120); // 10 bis 120 Minuten
        float fuelUsed = (duration / 60.0) * 6.5; // Verbrauch berechnen
        sendTripEnd(duration, fuelUsed);
    } 
    else if (chance < 1) {
        // 50 - 79 (30%) -> Trip Ende
        // Hier wird "Trip End" deutlich wahrscheinlicher
        currentFuel = random(15, 50);
        // Simuliere leichte Schwankung der Batterie
        currentBattery = 13.5 + (random(-5, 5) / 10.0); 
        sendStatus();
    }
    else if (chance < 1) {
        // 80 - 89 (10%) -> Fehler
        uint8_t errorCode = random(1, 5); // Code 1 bis 4
        sendError(errorCode);
    }
    else {
        // 90 - 99 (10%) -> Idle
        sendIdle();
    }
}

// --- LMIC SETUP (Heltec ESP32 LoRa V2) ---
const lmic_pinmap lmic_pins = {
    .nss = 18,
    .rxtx = LMIC_UNUSED_PIN,
    .rst = 14,
    .dio = {26, 35, 34}
};

void onEvent(ev_t ev) {
    switch(ev) {
        case EV_JOINING:
            Serial.println(F("Joining..."));
            break;
        case EV_JOINED:
            Serial.println(F("Joined!"));
            LMIC_setLinkCheckMode(0);
            break;
        case EV_TXCOMPLETE:
    Serial.println(F("TX Complete - Stoppe hier."));
    while(1) { 
        delay(0); // Endlosschleife ohne Neustart
    }
    break;
        case EV_JOIN_FAILED:
            Serial.println(F("Join failed!"));
            break;
        default:
            break;
    }
}

void do_send(osjob_t* j) {
    if (LMIC.opmode & OP_TXRXPEND) {
        Serial.println(F("TX pending, skip"));
    } else {
        preparePayload();
        LMIC_setTxData2(1, payload, sizeof(payload), 0);
        Serial.println(F("Packet queued"));
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println(F("\n=== Smart-Car LoRa Sender ==="));
    Serial.print(F("Vehicle ID: "));
    Serial.println(CURRENT_VEHICLE);
    
    // OLED Reset (Heltec)
    pinMode(16, OUTPUT);
    digitalWrite(16, LOW);
    delay(50);
    digitalWrite(16, HIGH);
    
    // LMIC init
    os_init();
    LMIC_reset();
    
    // EU868 Frequenz
    LMIC_setupChannel(0, 868100000, DR_RANGE_MAP(DR_SF12, DR_SF7), BAND_CENTI);
    
    // Start senden
    do_send(&sendjob);
}

void loop() {
    os_runloop_once();
}