#!/usr/bin/env python3
"""
OpenWeatherMap Service fuer Smart-Car
Kontextualisiert Fahrzeugdaten basierend auf Wetterbedingungen.
Inkl. Reifenempfehlungen und Fahrbedingungen.
"""

import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Konfiguration
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')
DEFAULT_LAT = os.environ.get('DEFAULT_LAT', '49.2354')  # Saarbrücken
DEFAULT_LON = os.environ.get('DEFAULT_LON', '6.9958')
CACHE_DURATION_SECONDS = 600  # 10 Minuten

# Cache fuer Wetterdaten
weather_cache = {}

# ===========================================
# OSTERN BERECHNUNG (für O-bis-O Regel)
# ===========================================
def get_easter_date(year):
    """
    Berechnet Ostersonntag nach Gauss-Algorithmus.
    """
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
    """
    Prüft ob wir in der Winterreifen-Saison sind (O-bis-O Regel).
    Oktober bis Ostern = Winterreifen empfohlen
    Ostern bis Oktober = Sommerreifen empfohlen
    """
    if date is None:
        date = datetime.now()
    
    year = date.year
    month = date.month
    
    # Oktober-Dezember: definitiv Wintersaison
    if month >= 10:
        return True
    
    # Januar-April: Ostern prüfen
    if month <= 4:
        easter = get_easter_date(year)
        # Vor Ostern = Wintersaison
        if date.date() < easter.date():
            return True
        # Nach Ostern = Sommersaison
        return False
    
    # Mai-September: Sommersaison
    return False


# ===========================================
# REIFEN-EMPFEHLUNGEN
# ===========================================
def get_tire_recommendation(temp_c, weather_main, date=None):
    """
    Gibt Reifenempfehlung basierend auf Witterung und O-bis-O Regel.
    
    Logik nach deutschen Empfehlungen:
    1. WITTERUNG hat Vorrang: Schnee/Eis = Winterreifen PFLICHT
    2. Temperatur: Dauerhaft >7°C = Sommerreifen (bessere Haftung)
    3. Saison: Oktober bis Ostern = Winterreifen, Ostern bis Oktober = Sommerreifen
    """
    if date is None:
        date = datetime.now()
    
    weather_lower = weather_main.lower() if weather_main else ''
    winter_season = is_winter_season(date)
    
    # ===========================================
    # PRIORITÄT 1: Winterliche Witterung = WINTERREIFEN PFLICHT
    # ===========================================
    winter_weather = weather_lower in ['snow', 'sleet', 'freezing rain', 'ice', 'hail']
    
    if winter_weather or temp_c <= 0:
        return {
            'type': 'winter',
            'required': True,
            'label': 'Winterreifen PFLICHT',
            'icon': '❄️',
            'reason': 'Schnee, Eis oder Temperaturen ≤0°C',
            'legal': '⚠️ Winterreifenpflicht! §2 Abs. 3a StVO',
            'color': '#2196F3',
            'urgency': 'critical',
            'action': 'Sofort Winterreifen aufziehen!'
        }
    
    # ===========================================
    # PRIORITÄT 2: Temperaturen ≤7°C = Winterreifen empfohlen
    # ===========================================
    if temp_c <= 7:
        return {
            'type': 'winter',
            'required': False,
            'label': 'Winterreifen empfohlen',
            'icon': '🌨️',
            'reason': f'Temperaturen unter 7°C ({temp_c:.1f}°C) - Gummimischung Winterreifen besser',
            'legal': 'Keine Pflicht, aber deutlich sicherer',
            'color': '#03A9F4',
            'urgency': 'recommended',
            'action': 'Winterreifen aufziehen für optimale Sicherheit'
        }
    
    # ===========================================
    # PRIORITÄT 3: Temperaturen >7°C = Sommerreifen empfohlen
    # ===========================================
    if temp_c > 7:
        # Aber Vorsicht in der Wintersaison
        if winter_season:
            return {
                'type': 'summer_possible',
                'required': False,
                'label': 'Sommerreifen möglich',
                'icon': '⚠️',
                'reason': f'Aktuell {temp_c:.1f}°C, aber noch Wintersaison (O-bis-O)',
                'legal': 'Wetterumschwung möglich - Winterreifen behalten',
                'color': '#FF9800',
                'urgency': 'info',
                'action': 'Wetter beobachten, bei stabilem Wetter >7°C wechseln'
            }
        else:
            # Sommersaison + warm = Sommerreifen optimal
            if temp_c >= 30:
                return {
                    'type': 'summer',
                    'required': False,
                    'label': 'Sommerreifen - Hitze beachten!',
                    'icon': '🌡️',
                    'reason': f'Hohe Temperaturen ({temp_c:.1f}°C)',
                    'legal': 'Reifendruck bei Hitze erhöht - prüfen!',
                    'color': '#FF9800',
                    'urgency': 'info',
                    'action': 'Reifendruck kontrollieren'
                }
            else:
                return {
                    'type': 'summer',
                    'required': False,
                    'label': 'Sommerreifen optimal',
                    'icon': '☀️',
                    'reason': f'Temperaturen dauerhaft >7°C ({temp_c:.1f}°C) - bessere Haftung mit Sommerreifen',
                    'legal': 'Sommerreifen haben bei Wärme kürzeren Bremsweg',
                    'color': '#4CAF50',
                    'urgency': 'optimal',
                    'action': 'Sommerreifen nutzen'
                }
    
    # Fallback
    return {
        'type': 'unknown',
        'required': False,
        'label': 'Keine Empfehlung',
        'icon': '❓',
        'reason': 'Wetterdaten unvollständig',
        'legal': '',
        'color': '#9E9E9E',
        'urgency': 'info',
        'action': 'Wetter manuell prüfen'
    }


def check_tire_mismatch(current_tires, recommended_type):
    """
    Prüft ob die aktuell montierten Reifen zur Empfehlung passen.
    
    Args:
        current_tires: 'summer', 'winter', 'allseason'
        recommended_type: 'summer', 'winter', 'summer_possible'
    
    Returns:
        dict mit mismatch-Info und Handlungsempfehlung
    """
    # Ganzjahresreifen sind immer OK (aber nicht optimal)
    if current_tires == 'allseason':
        return {
            'mismatch': False,
            'warning': 'Ganzjahresreifen montiert - Kompromiss bei Leistung',
            'change_needed': False,
            'urgency': 'info'
        }
    
    # Winterreifen empfohlen, aber Sommerreifen drauf
    if recommended_type == 'winter' and current_tires == 'summer':
        return {
            'mismatch': True,
            'warning': '⚠️ FALSCHE REIFEN! Winterreifen benötigt!',
            'change_needed': True,
            'urgency': 'critical'
        }
    
    # Sommerreifen optimal, aber Winterreifen drauf
    if recommended_type == 'summer' and current_tires == 'winter':
        return {
            'mismatch': True,
            'warning': 'Winterreifen bei warmem Wetter - höherer Verschleiß',
            'change_needed': True,
            'urgency': 'recommended'
        }
    
    # Sommerreifen möglich, Winterreifen drauf - OK
    if recommended_type == 'summer_possible' and current_tires == 'winter':
        return {
            'mismatch': False,
            'warning': 'Winterreifen OK - Wechsel optional bei stabilem Wetter',
            'change_needed': False,
            'urgency': 'info'
        }
    
    # Passende Reifen
    return {
        'mismatch': False,
        'warning': None,
        'change_needed': False,
        'urgency': 'ok'
    }


def get_road_condition(temp_c, weather_main, humidity, visibility):
    """
    Schätzt Straßenzustand basierend auf Wetterdaten.
    """
    weather_lower = weather_main.lower() if weather_main else ''
    
    conditions = []
    risk_level = 0  # 0-100
    
    # Nässe
    if weather_lower in ['rain', 'drizzle', 'thunderstorm']:
        conditions.append('Nasse Fahrbahn')
        risk_level += 20
        if weather_lower == 'thunderstorm':
            conditions.append('Gewitter')
            risk_level += 15
    
    # Schnee/Eis
    if weather_lower == 'snow':
        conditions.append('Schnee auf Fahrbahn möglich')
        risk_level += 40
    
    if temp_c <= 0:
        conditions.append('Glatteisgefahr')
        risk_level += 35
    elif temp_c <= 3:
        conditions.append('Frostgefahr')
        risk_level += 20
    
    # Nebel
    if visibility < 1000:
        conditions.append('Nebel')
        risk_level += 25
    elif visibility < 5000:
        conditions.append('Diesig')
        risk_level += 10
    
    # Feuchtigkeit + Kälte = Glätte
    if humidity > 90 and temp_c <= 5:
        conditions.append('Reifglätte möglich')
        risk_level += 15
    
    # Hitze
    if temp_c >= 35:
        conditions.append('Hitzeschäden möglich')
        risk_level += 10
    
    if not conditions:
        conditions.append('Trockene Fahrbahn')
    
    risk_level = min(100, risk_level)
    
    # Risiko-Kategorie
    if risk_level >= 60:
        risk_category = 'hoch'
        risk_color = '#F44336'  # Rot
    elif risk_level >= 30:
        risk_category = 'mittel'
        risk_color = '#FF9800'  # Orange
    else:
        risk_category = 'niedrig'
        risk_color = '#4CAF50'  # Grün
    
    return {
        'conditions': conditions,
        'risk_level': risk_level,
        'risk_category': risk_category,
        'risk_color': risk_color
    }

def get_weather(lat=None, lon=None):
    """
    Holt aktuelle Wetterdaten von OpenWeatherMap.
    Mit Fallback für Saarbrücken wenn API nicht verfügbar.
    """
    lat = lat or DEFAULT_LAT
    lon = lon or DEFAULT_LON
    cache_key = f"{lat},{lon}"
    
    # Cache pruefen
    if cache_key in weather_cache:
        cached = weather_cache[cache_key]
        age = (datetime.now() - cached['timestamp']).total_seconds()
        if age < CACHE_DURATION_SECONDS:
            return cached['data']
    
    # Fallback-Daten für Saarbrücken (Februar-typisches Winterwetter)
    def get_fallback_weather():
        month = datetime.now().month
        # Typische Durchschnittstemperaturen Saarbrücken
        monthly_temps = {1: 2, 2: 3, 3: 7, 4: 11, 5: 15, 6: 18, 7: 20, 8: 20, 9: 16, 10: 11, 11: 6, 12: 3}
        temp = monthly_temps.get(month, 10)
        return {
            'temperature_c': temp,
            'feels_like_c': temp - 2,
            'humidity_percent': 75,
            'pressure_hpa': 1015,
            'wind_speed_ms': 3,
            'wind_direction_deg': 270,
            'clouds_percent': 60,
            'visibility_m': 10000,
            'weather_main': 'Clouds',
            'weather_description': 'Bewölkt (Fallback)',
            'weather_icon': '04d',
            'location_name': 'Saarbrücken',
            'timestamp': datetime.now().isoformat(),
            'warnings': [],
            'is_fallback': True,
            'configured': True
        }
    
    if not OPENWEATHERMAP_API_KEY:
        fallback = get_fallback_weather()
        fallback['error'] = 'API Key nicht konfiguriert'
        fallback['configured'] = False
        return fallback
    
    try:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHERMAP_API_KEY,
            'units': 'metric',
            'lang': 'de'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Relevante Daten extrahieren
        weather_data = {
            'temperature_c': data.get('main', {}).get('temp', 0),
            'feels_like_c': data.get('main', {}).get('feels_like', 0),
            'humidity_percent': data.get('main', {}).get('humidity', 0),
            'pressure_hpa': data.get('main', {}).get('pressure', 0),
            'wind_speed_ms': data.get('wind', {}).get('speed', 0),
            'wind_direction_deg': data.get('wind', {}).get('deg', 0),
            'clouds_percent': data.get('clouds', {}).get('all', 0),
            'visibility_m': data.get('visibility', 10000),
            'weather_main': data.get('weather', [{}])[0].get('main', 'Unknown'),
            'weather_description': data.get('weather', [{}])[0].get('description', ''),
            'weather_icon': data.get('weather', [{}])[0].get('icon', ''),
            'location_name': data.get('name', ''),
            'timestamp': datetime.now().isoformat(),
            'sunrise': datetime.fromtimestamp(data.get('sys', {}).get('sunrise', 0)).isoformat(),
            'sunset': datetime.fromtimestamp(data.get('sys', {}).get('sunset', 0)).isoformat()
        }
        
        # Fahrzeug-relevante Warnungen ableiten
        weather_data['warnings'] = []
        
        # Glatteis-Warnung
        if weather_data['temperature_c'] <= 3:
            weather_data['warnings'].append({
                'type': 'frost_warning',
                'severity': 'high' if weather_data['temperature_c'] <= 0 else 'medium',
                'message': 'Glatteisgefahr - Vorsicht beim Fahren'
            })
        
        # Sturm-Warnung
        if weather_data['wind_speed_ms'] > 15:
            weather_data['warnings'].append({
                'type': 'wind_warning',
                'severity': 'high' if weather_data['wind_speed_ms'] > 25 else 'medium',
                'message': 'Starker Wind - Fahrzeug sichern'
            })
        
        # Nebel-Warnung
        if weather_data['visibility_m'] < 1000:
            weather_data['warnings'].append({
                'type': 'fog_warning',
                'severity': 'high' if weather_data['visibility_m'] < 200 else 'medium',
                'message': 'Schlechte Sicht - Langsam fahren'
            })
        
        # Hitze-Warnung
        if weather_data['temperature_c'] >= 35:
            weather_data['warnings'].append({
                'type': 'heat_warning',
                'severity': 'high',
                'message': 'Extreme Hitze - Klimaanlage und Kuehlung pruefen'
            })
        
        # Regen/Schnee erkennen
        weather_main = weather_data['weather_main'].lower()
        if weather_main in ['rain', 'drizzle', 'thunderstorm']:
            weather_data['warnings'].append({
                'type': 'rain_warning',
                'severity': 'medium',
                'message': 'Regen - Auf Aquaplaning achten'
            })
        elif weather_main == 'snow':
            weather_data['warnings'].append({
                'type': 'snow_warning',
                'severity': 'high',
                'message': 'Schneefall - Winterreifen empfohlen'
            })
        
        # Fahrbedingungen bewerten (1-5, 5=optimal)
        driving_score = 5
        if weather_data['temperature_c'] <= 0 or weather_data['temperature_c'] >= 35:
            driving_score -= 1
        if weather_data['visibility_m'] < 5000:
            driving_score -= 1
        if weather_data['wind_speed_ms'] > 10:
            driving_score -= 1
        if weather_main in ['rain', 'snow', 'thunderstorm']:
            driving_score -= 1
        
        weather_data['driving_conditions'] = max(1, driving_score)
        weather_data['driving_conditions_text'] = {
            5: 'Optimal',
            4: 'Gut',
            3: 'Maessig',
            2: 'Schlecht',
            1: 'Gefaehrlich'
        }.get(weather_data['driving_conditions'], 'Unbekannt')
        
        # Cache aktualisieren
        weather_cache[cache_key] = {
            'data': weather_data,
            'timestamp': datetime.now()
        }
        
        return weather_data
        
    except requests.exceptions.RequestException as e:
        # Bei API-Fehler: Fallback-Daten zurückgeben
        fallback = get_fallback_weather()
        fallback['error'] = f'API-Fehler: {str(e)}'
        print(f"Wetter-API Fehler, nutze Fallback: {e}")
        return fallback
    except Exception as e:
        fallback = get_fallback_weather()
        fallback['error'] = f'Verarbeitung fehlgeschlagen: {str(e)}'
        return fallback


@app.route('/weather', methods=['GET'])
def weather_endpoint():
    """
    GET /weather?lat=...&lon=...
    Gibt aktuelle Wetterdaten zurueck.
    """
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    
    data = get_weather(lat, lon)
    return jsonify(data)


@app.route('/weather/vehicle/<vehicle_id>', methods=['GET'])
def weather_for_vehicle(vehicle_id):
    """
    GET /weather/vehicle/VH001
    Holt Wetter basierend auf letzter GPS-Position des Fahrzeugs.
    """
    # TODO: GPS-Position aus InfluxDB abrufen
    # Vorerst Default-Location verwenden
    data = get_weather()
    data['vehicle_id'] = vehicle_id
    return jsonify(data)


@app.route('/weather/context', methods=['POST'])
def weather_context():
    """
    POST /weather/context
    Body: {"vehicle_id": "VH001", "lat": 51.1, "lon": 10.4, "event_type": "trip_start"}
    
    Gibt kontextualisierte Wetterdaten fuer ein Ereignis zurueck.
    """
    body = request.get_json() or {}
    vehicle_id = body.get('vehicle_id', 'UNKNOWN')
    lat = body.get('lat')
    lon = body.get('lon')
    event_type = body.get('event_type', 'general')
    
    weather_data = get_weather(lat, lon)
    
    # Kontext-spezifische Empfehlungen
    context_data = {
        'vehicle_id': vehicle_id,
        'event_type': event_type,
        'weather': weather_data,
        'recommendations': []
    }
    
    if 'error' not in weather_data:
        # Empfehlungen basierend auf Event-Typ
        if event_type == 'trip_start':
            if weather_data.get('temperature_c', 20) <= 0:
                context_data['recommendations'].append('Motor vorwaermen empfohlen')
            if weather_data.get('visibility_m', 10000) < 1000:
                context_data['recommendations'].append('Nebelscheinwerfer einschalten')
            if weather_data.get('weather_main', '').lower() in ['rain', 'snow']:
                context_data['recommendations'].append('Laengeren Bremsweg einplanen')
        
        elif event_type == 'parking':
            if weather_data.get('temperature_c', 20) >= 30:
                context_data['recommendations'].append('Sonnenschutz verwenden')
            if weather_data.get('wind_speed_ms', 0) > 15:
                context_data['recommendations'].append('Geschuetzten Parkplatz suchen')
    
    return jsonify(context_data)


@app.route('/health', methods=['GET'])
def health():
    """Health Check Endpoint."""
    api_configured = bool(OPENWEATHERMAP_API_KEY)
    return jsonify({
        'status': 'healthy',
        'service': 'weather-service',
        'api_configured': api_configured,
        'cache_entries': len(weather_cache)
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Weather Service startet auf Port {port}")
    print(f"API Key konfiguriert: {bool(OPENWEATHERMAP_API_KEY)}")
    app.run(host='0.0.0.0', port=port, debug=False)
