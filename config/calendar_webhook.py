#!/usr/bin/env python3
"""
Webhook Server fuer Google Calendar Integration.
Empfaengt Alert-Events von Node-RED und erstellt Google Calendar Termine.
"""

from flask import Flask, request, jsonify
import json
import os
import sys
from datetime import datetime, timedelta

app = Flask(__name__)

# Google API importieren
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Google API nicht verfuegbar - Events werden nur geloggt")

# Konfiguration
KEY_FILE = os.environ.get('GOOGLE_KEY_FILE', '/config/google-calendar-key.json')
ALERTS_FILE = os.environ.get('ALERTS_FILE', '/config/alerts.json')
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Cache
_service = None
_config = None


def load_config():
    """Laedt die Alert-Konfiguration."""
    global _config
    if _config is None:
        try:
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                _config = json.load(f)
        except:
            _config = {}
    return _config


def get_calendar_service():
    """Erstellt einen authentifizierten Google Calendar Service."""
    global _service
    
    if _service is not None:
        return _service
    
    if not GOOGLE_API_AVAILABLE:
        return None
    
    if not os.path.exists(KEY_FILE):
        print("Key-Datei nicht gefunden: " + KEY_FILE)
        return None
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            KEY_FILE, scopes=SCOPES
        )
        _service = build('calendar', 'v3', credentials=credentials)
        
        # Test: Versuche die Kalender-Liste abzurufen
        try:
            calendars = _service.calendarList().list().execute()
            print(f"Google Calendar Service verbunden - {len(calendars.get('items', []))} Kalender gefunden")
        except Exception as e:
            print(f"Kalender-List Fehler (aber Service ist verbunden): {str(e)}")
        
        return _service
    except Exception as e:
        print("Service-Fehler beim Erstellen: " + str(e))
        import traceback
        traceback.print_exc()
        return None


def create_event(event_data):
    """Erstellt einen Kalender-Termin."""
    config = load_config()
    google_config = config.get('google_calendar', {})
    
    if not google_config.get('enabled', False):
        return {'success': False, 'error': 'Google Calendar deaktiviert'}
    
    calendar_id = google_config.get('calendar_id', '')
    if not calendar_id or calendar_id == 'DEINE_KALENDER_ID_HIER':
        return {'success': False, 'error': 'Keine Kalender-ID konfiguriert'}
    
    service = get_calendar_service()
    if not service:
        print("Event (nicht gesendet): " + event_data.get('summary', event_data.get('title', 'Unknown')))
        return {'success': False, 'error': 'Google Calendar Service nicht verfuegbar'}
    
    # Event aufbereiten
    if 'start' in event_data and 'dateTime' in event_data['start']:
        start = datetime.fromisoformat(event_data['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(event_data['end']['dateTime'].replace('Z', '+00:00'))
    else:
        start = datetime.now() + timedelta(hours=1)
        start = start.replace(minute=0, second=0, microsecond=0)
        duration = event_data.get('duration_minutes', 30)
        end = start + timedelta(minutes=duration)
    
    title = event_data.get('summary', event_data.get('title', 'Smart-Car Alert'))
    description = event_data.get('description', '')
    
    # Farbcode aus Payload oder basierend auf Titel
    color_id = event_data.get('colorId', '9')
    if not color_id:
        if 'KRITISCH' in title or 'DRINGEND' in title:
            color_id = '11'  # Rot
        elif 'HOCH' in title:
            color_id = '6'   # Orange
        else:
            color_id = '9'   # Blau
    
    event = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start.isoformat(),
            'timeZone': 'Europe/Berlin',
        },
        'end': {
            'dateTime': end.isoformat(),
            'timeZone': 'Europe/Berlin',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 30},
                {'method': 'email', 'minutes': 60},
            ],
        },
        'colorId': color_id,
    }
    
    try:
        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        print("Termin erstellt: " + title)
        return {
            'success': True,
            'event_id': created['id'],
            'link': created.get('htmlLink', '')
        }
    except Exception as e:
        error_str = str(e)
        print(f"Fehler beim Erstellen des Events: {error_str}")
        
        # Detaillierte Fehlermeldung für JWT-Probleme
        if 'invalid_grant' in error_str:
            print("HINWEIS: JWT-Fehler - Dies kann bedeuten:")
            print("1. Der Kalender wurde dem Service Account NICHT freigegeben")
            print("2. Der private Key ist ungültig")
            print("3. Die Kalender-ID ist falsch")
            print(f"   Service Account: {service._credentials.service_account_email if hasattr(service, '_credentials') else 'unbekannt'}")
            print(f"   Kalender ID: {calendar_id}")
        
        import traceback
        traceback.print_exc()
        
        return {'success': False, 'error': error_str}


@app.route('/health', methods=['GET'])
def health():
    """Health Check Endpoint."""
    return jsonify({'status': 'ok', 'google_api': GOOGLE_API_AVAILABLE})


@app.route('/event', methods=['POST'])
def create_calendar_event():
    """Erstellt einen Kalender-Termin aus dem Request."""
    try:
        event_data = request.get_json()
        if not event_data:
            return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400
        
        print("Event empfangen: " + event_data.get('summary', event_data.get('title', '?')))
        result = create_event(event_data)
        
        status_code = 200 if result.get('success') else 500
        return jsonify(result), status_code
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/test', methods=['GET'])
def test_event():
    """Erstellt einen Test-Termin."""
    test_data = {
        'summary': 'TEST: Smart-Car Kalender',
        'description': 'Test-Termin der Kalender-Integration.',
        'duration_minutes': 30
    }
    result = create_event(test_data)
    return jsonify(result)


if __name__ == '__main__':
    print("=" * 50)
    print("Smart-Car Calendar Webhook Server")
    print("=" * 50)
    
    config = load_config()
    google_config = config.get('google_calendar', {})
    
    print("Google API verfuegbar: " + str(GOOGLE_API_AVAILABLE))
    print("Google Calendar enabled: " + str(google_config.get('enabled', False)))
    print("Calendar ID: " + google_config.get('calendar_id', 'nicht konfiguriert'))
    print("Key File: " + KEY_FILE)
    print("Key File exists: " + str(os.path.exists(KEY_FILE)))
    
    # Versuche Service zu verbinden beim Start
    service = get_calendar_service()
    if service:
        print("✓ Google Calendar Service erfolgreich verbunden!")
    else:
        print("✗ Google Calendar Service FEHLER!")
    
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
