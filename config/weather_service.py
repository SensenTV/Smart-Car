#!/usr/bin/env python3
"""
OpenWeatherMap Service fuer Smart-Car
Kontextualisiert Fahrzeugdaten basierend auf Wetterbedingungen.
"""

import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Konfiguration
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')
DEFAULT_LAT = os.environ.get('DEFAULT_LAT', '51.1657')  # Deutschland Mitte
DEFAULT_LON = os.environ.get('DEFAULT_LON', '10.4515')
CACHE_DURATION_SECONDS = 600  # 10 Minuten

# Cache fuer Wetterdaten
weather_cache = {}

def get_weather(lat=None, lon=None):
    """
    Holt aktuelle Wetterdaten von OpenWeatherMap.
    """
    if not OPENWEATHERMAP_API_KEY:
        return {'error': 'API Key nicht konfiguriert', 'configured': False}
    
    lat = lat or DEFAULT_LAT
    lon = lon or DEFAULT_LON
    cache_key = f"{lat},{lon}"
    
    # Cache pruefen
    if cache_key in weather_cache:
        cached = weather_cache[cache_key]
        age = (datetime.now() - cached['timestamp']).total_seconds()
        if age < CACHE_DURATION_SECONDS:
            return cached['data']
    
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
        return {'error': f'API-Fehler: {str(e)}', 'configured': True}
    except Exception as e:
        return {'error': f'Verarbeitung fehlgeschlagen: {str(e)}', 'configured': True}


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
