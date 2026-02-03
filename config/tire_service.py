#!/usr/bin/env python3
"""
Reifen-Check Service für Smart-Car
Prüft Wetter, vergleicht mit montierten Reifen und erstellt Kalender-Einträge.
"""

import os
import sys
import json
import requests
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# InfluxDB Import
try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUX_AVAILABLE = True
except ImportError:
    INFLUX_AVAILABLE = False
    print("⚠️ InfluxDB Client nicht installiert")

# Google Calendar Import
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("⚠️ Google API nicht installiert - Kalender-Integration deaktiviert")

app = Flask(__name__)

# Konfiguration
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
VEHICLES_JSON = os.path.join(CONFIG_DIR, "vehicles.json")
ALERTS_JSON = os.path.join(CONFIG_DIR, "alerts.json")
GOOGLE_KEY_FILE = os.path.join(CONFIG_DIR, "google-calendar-key.json")
WEATHER_SERVICE_URL = os.environ.get('WEATHER_SERVICE_URL', 'http://weather-service:5001')
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

# InfluxDB Config
INFLUX_URL = os.environ.get('INFLUX_URL', 'http://influxdb:8086')
INFLUX_TOKEN = os.environ.get('INFLUX_TOKEN', 'vehicle-admin-token')
INFLUX_ORG = os.environ.get('INFLUX_ORG', 'vehicle_org')
INFLUX_BUCKET = os.environ.get('INFLUX_BUCKET', 'vehicle_data')

# Cooldown für Benachrichtigungen (verhindert Spam)
notification_cooldown = {}
COOLDOWN_HOURS = 24


def load_vehicles():
    """Lädt Fahrzeugkonfiguration."""
    try:
        with open(VEHICLES_JSON, 'r', encoding='utf-8') as f:
            return json.load(f).get('vehicles', [])
    except Exception as e:
        print(f"Fehler beim Laden der Fahrzeuge: {e}")
        return []


def save_vehicles(vehicles):
    """Speichert Fahrzeugkonfiguration."""
    try:
        with open(VEHICLES_JSON, 'w', encoding='utf-8') as f:
            json.dump({'vehicles': vehicles}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Fehler beim Speichern: {e}")
        return False


def get_weather():
    """Holt aktuelle Wetterdaten vom Weather-Service."""
    try:
        response = requests.get(f"{WEATHER_SERVICE_URL}/weather", timeout=10)
        return response.json()
    except Exception as e:
        print(f"Weather-Service nicht erreichbar: {e}")
        return None


def get_easter_date(year):
    """Berechnet Ostersonntag."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime(year, month, day)


def is_winter_season(date=None):
    """Prüft ob Wintersaison (O-bis-O)."""
    if date is None:
        date = datetime.now()
    
    year = date.year
    month = date.month
    
    if month >= 10:
        return True
    
    if month <= 4:
        easter = get_easter_date(year)
        return date.date() < easter.date()
    
    return False


def get_tire_recommendation(temp_c, weather_main):
    """
    Berechnet Reifenempfehlung.
    
    Priorität:
    1. Witterung (Schnee/Eis) = Winterreifen PFLICHT
    2. Temperatur ≤7°C = Winterreifen empfohlen
    3. Temperatur >7°C = Sommerreifen (bessere Haftung)
    4. Saison O-bis-O als Orientierung
    """
    weather_lower = weather_main.lower() if weather_main else ''
    date = datetime.now()
    winter_season = is_winter_season(date)
    
    # Winterliche Witterung = PFLICHT
    winter_weather = weather_lower in ['snow', 'sleet', 'freezing rain', 'ice', 'hail']
    
    if winter_weather or temp_c <= 0:
        return {
            'recommended': 'winter',
            'urgency': 'critical',
            'label': 'Winterreifen PFLICHT',
            'reason': 'Schnee, Eis oder Frost',
            'legal_warning': True
        }
    
    if temp_c <= 7:
        return {
            'recommended': 'winter',
            'urgency': 'high',
            'label': 'Winterreifen empfohlen',
            'reason': f'Temperatur {temp_c:.1f}°C - Winterreifen haben bessere Haftung',
            'legal_warning': False
        }
    
    # temp > 7°C
    if winter_season:
        return {
            'recommended': 'winter',
            'urgency': 'low',
            'label': 'Winterreifen behalten',
            'reason': f'Noch Wintersaison (O-bis-O), Wetter kann umschlagen',
            'legal_warning': False
        }
    else:
        return {
            'recommended': 'summer',
            'urgency': 'medium',
            'label': 'Sommerreifen empfohlen',
            'reason': f'Temperatur {temp_c:.1f}°C - Sommerreifen haben kürzeren Bremsweg',
            'legal_warning': False
        }


def check_tire_change_needed(vehicle, recommendation):
    """
    Prüft ob Reifenwechsel nötig ist.
    """
    current = vehicle.get('tires', {}).get('current', 'unknown')
    recommended = recommendation['recommended']
    urgency = recommendation['urgency']
    
    # Ganzjahresreifen - immer OK
    if current == 'allseason':
        return {
            'change_needed': False,
            'message': 'Ganzjahresreifen montiert',
            'urgency': 'ok'
        }
    
    # Passende Reifen
    if current == recommended:
        return {
            'change_needed': False,
            'message': f'{current.capitalize()}reifen montiert - passt!',
            'urgency': 'ok'
        }
    
    # Falsche Reifen
    if current == 'summer' and recommended == 'winter':
        return {
            'change_needed': True,
            'message': f'⚠️ Sommerreifen montiert, aber {recommendation["label"]}!',
            'urgency': urgency,
            'action': 'Auf Winterreifen wechseln'
        }
    
    if current == 'winter' and recommended == 'summer':
        return {
            'change_needed': True,
            'message': 'Winterreifen bei warmem Wetter - erhöhter Verschleiß',
            'urgency': 'low',
            'action': 'Auf Sommerreifen wechseln'
        }
    
    return {
        'change_needed': False,
        'message': 'Status unbekannt',
        'urgency': 'unknown'
    }


def create_calendar_event(vehicle, check_result, recommendation):
    """Erstellt Kalender-Termin für Reifenwechsel."""
    if not GOOGLE_API_AVAILABLE:
        print("Google API nicht verfügbar")
        return None
    
    if not os.path.exists(GOOGLE_KEY_FILE):
        print(f"Google Key nicht gefunden: {GOOGLE_KEY_FILE}")
        return None
    
    # Cooldown prüfen
    cooldown_key = f"{vehicle['vehicle_id']}_tire_change"
    if cooldown_key in notification_cooldown:
        last_notification = notification_cooldown[cooldown_key]
        if datetime.now() - last_notification < timedelta(hours=COOLDOWN_HOURS):
            print(f"Cooldown aktiv für {vehicle['vehicle_id']}")
            return None
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_FILE,
            scopes=['https://www.googleapis.com/auth/calendar.events']
        )
        service = build('calendar', 'v3', credentials=credentials)
        
        # Termin in 2 Tagen
        start_time = datetime.now() + timedelta(days=2)
        start_time = start_time.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        urgency_prefix = "🔴 DRINGEND: " if check_result['urgency'] == 'critical' else "🔶 "
        
        event = {
            'summary': f"{urgency_prefix}Reifenwechsel {vehicle['display_name']}",
            'description': f"""Fahrzeug: {vehicle['display_name']}
Kennzeichen: {vehicle.get('license_plate', 'N/A')}

Aktuell montiert: {vehicle.get('tires', {}).get('current', 'unbekannt').capitalize()}reifen
Empfehlung: {recommendation['label']}
Grund: {recommendation['reason']}

{check_result['message']}

---
Automatisch erstellt von Smart-Car""",
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Europe/Berlin',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Europe/Berlin',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60},
                    {'method': 'email', 'minutes': 1440},  # 1 Tag vorher
                ],
            },
        }
        
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        notification_cooldown[cooldown_key] = datetime.now()
        
        print(f"✅ Kalender-Termin erstellt: {created_event.get('htmlLink')}")
        return created_event.get('id')
        
    except Exception as e:
        print(f"Fehler beim Erstellen des Kalender-Termins: {e}")
        return None


def check_all_vehicles():
    """Prüft alle Fahrzeuge auf Reifenwechsel-Bedarf."""
    vehicles = load_vehicles()
    weather = get_weather()
    
    # Prüfe ob Wetterdaten nutzbar sind (auch mit Fallback)
    if not weather or weather.get('temperature_c') is None:
        return {
            'success': False,
            'error': 'Wetterdaten nicht verfügbar',
            'weather_error': weather.get('error') if weather else 'Service nicht erreichbar'
        }
    
    temp = weather.get('temperature_c', 10)
    weather_main = weather.get('weather_main', '')
    
    recommendation = get_tire_recommendation(temp, weather_main)
    
    results = []
    for vehicle in vehicles:
        vehicle_id = vehicle.get('vehicle_id')
        current_tires = vehicle.get('tires', {}).get('current', 'unknown')
        
        check = check_tire_change_needed(vehicle, recommendation)
        
        result = {
            'vehicle_id': vehicle_id,
            'display_name': vehicle.get('display_name'),
            'current_tires': current_tires,
            'recommendation': recommendation,
            'check_result': check,
            'calendar_event_created': False
        }
        
        # Bei kritischem Wechselbedarf -> Kalender-Eintrag
        if check['change_needed'] and check['urgency'] in ['critical', 'high']:
            event_id = create_calendar_event(vehicle, check, recommendation)
            result['calendar_event_created'] = event_id is not None
        
        results.append(result)
    
    return {
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'weather': {
            'temperature_c': temp,
            'condition': weather_main,
            'location': weather.get('location_name', 'Unbekannt')
        },
        'recommendation': recommendation,
        'winter_season': is_winter_season(),
        'easter_date': get_easter_date(datetime.now().year).strftime('%Y-%m-%d'),
        'vehicles': results
    }


# ===========================================
# API ENDPOINTS
# ===========================================

@app.route('/tires/check', methods=['GET'])
def check_tires():
    """
    GET /tires/check
    Prüft alle Fahrzeuge auf Reifenwechsel-Bedarf.
    """
    result = check_all_vehicles()
    return jsonify(result)


@app.route('/tires/check/<vehicle_id>', methods=['GET'])
def check_vehicle_tires(vehicle_id):
    """
    GET /tires/check/VW-Passat-B5-001
    Prüft ein spezifisches Fahrzeug.
    """
    vehicles = load_vehicles()
    vehicle = next((v for v in vehicles if v.get('vehicle_id') == vehicle_id), None)
    
    if not vehicle:
        return jsonify({'error': f'Fahrzeug {vehicle_id} nicht gefunden'}), 404
    
    weather = get_weather()
    if not weather or weather.get('temperature_c') is None:
        return jsonify({'error': 'Wetterdaten nicht verfügbar'}), 503
    
    temp = weather.get('temperature_c', 10)
    weather_main = weather.get('weather_main', '')
    
    recommendation = get_tire_recommendation(temp, weather_main)
    check = check_tire_change_needed(vehicle, recommendation)
    
    return jsonify({
        'vehicle_id': vehicle_id,
        'display_name': vehicle.get('display_name'),
        'current_tires': vehicle.get('tires', {}).get('current', 'unknown'),
        'tire_info': vehicle.get('tires', {}),
        'weather': {
            'temperature_c': temp,
            'condition': weather_main
        },
        'recommendation': recommendation,
        'check_result': check,
        'winter_season': is_winter_season()
    })


@app.route('/tires/set/<vehicle_id>', methods=['POST'])
def set_vehicle_tires(vehicle_id):
    """
    POST /tires/set/VW-Passat-B5-001
    Body: {"current": "winter"} oder {"current": "summer"}
    
    Aktualisiert die aktuell montierten Reifen.
    """
    vehicles = load_vehicles()
    vehicle_idx = next((i for i, v in enumerate(vehicles) if v.get('vehicle_id') == vehicle_id), None)
    
    if vehicle_idx is None:
        return jsonify({'error': f'Fahrzeug {vehicle_id} nicht gefunden'}), 404
    
    body = request.get_json() or {}
    new_tire_type = body.get('current', '').lower()
    
    if new_tire_type not in ['summer', 'winter', 'allseason']:
        return jsonify({'error': 'Ungültiger Reifentyp. Erlaubt: summer, winter, allseason'}), 400
    
    # Update
    if 'tires' not in vehicles[vehicle_idx]:
        vehicles[vehicle_idx]['tires'] = {}
    
    vehicles[vehicle_idx]['tires']['current'] = new_tire_type
    vehicles[vehicle_idx]['tires']['last_change'] = datetime.now().strftime('%Y-%m-%d')
    
    if save_vehicles(vehicles):
        return jsonify({
            'success': True,
            'vehicle_id': vehicle_id,
            'current_tires': new_tire_type,
            'last_change': vehicles[vehicle_idx]['tires']['last_change']
        })
    else:
        return jsonify({'error': 'Speichern fehlgeschlagen'}), 500


@app.route('/tires/status', methods=['GET'])
def tire_status():
    """
    GET /tires/status
    Gibt Status aller Fahrzeuge für Grafana zurück.
    """
    vehicles = load_vehicles()
    weather = get_weather()
    
    # Prüfe ob Wetterdaten nutzbar sind (auch mit Fallback)
    if weather and weather.get('temperature_c') is not None:
        temp = weather.get('temperature_c', 10)
        weather_main = weather.get('weather_main', '')
        recommendation = get_tire_recommendation(temp, weather_main)
    else:
        recommendation = {'recommended': 'unknown', 'label': 'Wetter nicht verfügbar'}
    
    status_list = []
    for vehicle in vehicles:
        current = vehicle.get('tires', {}).get('current', 'unknown')
        last_change = vehicle.get('tires', {}).get('last_change', 'unbekannt')
        
        # Status-Ampel
        if current == 'allseason':
            status = 'ok'
            status_text = 'Ganzjahresreifen'
        elif current == recommendation.get('recommended'):
            status = 'ok'
            status_text = 'Passend'
        elif recommendation.get('recommended') == 'winter' and current == 'summer':
            status = 'critical'
            status_text = 'WECHSEL NÖTIG!'
        elif recommendation.get('recommended') == 'summer' and current == 'winter':
            status = 'warning'
            status_text = 'Wechsel empfohlen'
        else:
            status = 'unknown'
            status_text = 'Unbekannt'
        
        status_list.append({
            'vehicle_id': vehicle.get('vehicle_id'),
            'display_name': vehicle.get('display_name'),
            'current_tires': current,
            'last_change': last_change,
            'status': status,
            'status_text': status_text,
            'tire_brand': vehicle.get('tires', {}).get(current, {}).get('brand', 'N/A'),
            'tire_size': vehicle.get('tires', {}).get(current, {}).get('size', 'N/A')
        })
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'recommendation': recommendation,
        'vehicles': status_list
    })


@app.route('/health', methods=['GET'])
def health():
    """Health Check."""
    return jsonify({
        'status': 'healthy',
        'service': 'tire-service',
        'google_api_available': GOOGLE_API_AVAILABLE,
        'google_key_exists': os.path.exists(GOOGLE_KEY_FILE)
    })


def write_tire_data_to_influx():
    """Schreibt aktuelle Reifendaten nach InfluxDB."""
    if not INFLUX_AVAILABLE:
        return False
    
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        vehicles = load_vehicles()
        weather = get_weather()
        
        # Wetterdaten extrahieren - Fallback-Daten sind OK, solange temperature_c vorhanden ist
        if weather and weather.get('temperature_c') is not None:
            temp_c = weather.get('temperature_c', 3)
            weather_main = weather.get('weather_main', 'Clear')
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Wetter: {temp_c}°C, {weather_main} (Fallback: {weather.get('is_fallback', False)})")
        else:
            temp_c = 3  # Standard-Fallback für Saarbrücken Februar
            weather_main = 'Clear'
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Kein Wetter verfügbar, nutze Default: {temp_c}°C")
        
        recommendation = get_tire_recommendation(temp_c, weather_main)
        recommendation['temperature'] = temp_c
        recommendation['is_winter_season'] = is_winter_season()
        
        points = []
        for vehicle in vehicles:
            tires = vehicle.get('tires', {})
            current = tires.get('current', 'unknown')
            recommended = recommendation.get('recommended', 'unknown')
            
            # Status berechnen - auch aktuelle Reifen-Typen berücksichtigen
            if current == 'allseason':
                status_value = 1
                status_text = "Ganzjahresreifen"
                status = "ok"
            elif current == recommended:
                status_value = 0
                status_text = "Passend"
                status = "ok"
            elif current == 'unknown':
                status_value = -1
                status_text = "Unbekannt"
                status = "unknown"
            elif recommendation.get('urgency') == 'critical':
                status_value = 3
                status_text = "WECHSEL NÖTIG!"
                status = "critical"
            elif recommendation.get('urgency') == 'high':
                status_value = 2
                status_text = "Wechsel empfohlen"
                status = "warning"
            else:
                status_value = 1
                status_text = "Wechsel optional"
                status = "info"
            
            # Numerischen Wert für Grafana: 2=winter, 1=summer, 0=allseason
            current_tires_value = 2 if current == 'winter' else (1 if current == 'summer' else 0)
            recommended_value = 2 if recommended == 'winter' else (1 if recommended == 'summer' else 0)
            
            point = Point("tire_status") \
                .tag("vehicle_id", vehicle.get('vehicle_id', 'unknown')) \
                .tag("display_name", vehicle.get('display_name', 'Unbekannt')) \
                .field("current_tires", current) \
                .field("current_tires_value", current_tires_value) \
                .field("recommended", recommended) \
                .field("recommended_value", recommended_value) \
                .field("status", status) \
                .field("status_value", status_value) \
                .field("status_text", status_text) \
                .field("tire_brand", tires.get(current, {}).get('brand', 'N/A')) \
                .field("tire_size", tires.get(current, {}).get('size', 'N/A')) \
                .field("recommendation_label", recommendation.get('label', 'Unbekannt')) \
                .field("temperature", float(temp_c)) \
                .field("is_winter_season", 1 if recommendation.get('is_winter_season') else 0)
            
            points.append(point)
        
        write_api.write(bucket=INFLUX_BUCKET, record=points)
        client.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] InfluxDB: {len(points)} Fahrzeuge geschrieben ✓")
        return True
        
    except Exception as e:
        print(f"InfluxDB Fehler: {e}")
        return False


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    print(f"Tire-Service startet auf Port {port}")
    print(f"Wintersaison: {is_winter_season()}")
    print(f"Ostern {datetime.now().year}: {get_easter_date(datetime.now().year).strftime('%d.%m.%Y')}")
    print(f"InfluxDB verfügbar: {INFLUX_AVAILABLE}")
    
    # Starte Hintergrund-Thread für InfluxDB-Updates
    def influx_updater():
        """Schreibt periodisch Reifendaten nach InfluxDB."""
        print("DEBUG: influx_updater gestartet - warte 10 Sekunden...")
        time.sleep(10)  # Warte bis Services bereit
        counter = 0
        while True:
            counter += 1
            print(f"DEBUG: InfluxDB Update #{counter} (alle 60s)")
            try:
                result = write_tire_data_to_influx()
                if not result:
                    print("WARNING: write_tire_data_to_influx returned False")
            except Exception as e:
                print(f"InfluxDB Update Fehler: {e}")
                import traceback
                traceback.print_exc()
            time.sleep(60)  # Alle 60 Sekunden
    
    if INFLUX_AVAILABLE:
        updater_thread = threading.Thread(target=influx_updater, daemon=True)
        updater_thread.start()
        print("InfluxDB Updater gestartet (alle 60s)")
    
    app.run(host='0.0.0.0', port=port, debug=False)
