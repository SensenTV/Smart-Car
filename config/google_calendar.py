#!/usr/bin/env python3
"""
Google Calendar Integration für Smart-Car Alerts
Erstellt automatisch Kalender-Termine bei IoT-Alerts.

Voraussetzungen:
1. Google Cloud Projekt mit Calendar API aktiviert
2. Service Account mit JSON-Schlüssel in google-calendar-key.json
3. Kalender mit dem Service Account geteilt (Schreibzugriff)
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Versuche Google API Client zu importieren
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("⚠️  Google API Client nicht installiert!")
    print("   Installiere mit: pip install google-api-python-client google-auth")

# Konfiguration
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(CONFIG_DIR, "google-calendar-key.json")
ALERTS_FILE = os.path.join(CONFIG_DIR, "alerts.json")

# Scopes für Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def load_config():
    """Lädt die Alert-Konfiguration."""
    try:
        with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Konfiguration nicht gefunden: {ALERTS_FILE}")
        return None


def get_calendar_service():
    """Erstellt einen authentifizierten Google Calendar Service."""
    if not GOOGLE_API_AVAILABLE:
        return None
    
    if not os.path.exists(KEY_FILE):
        print(f"❌ Service Account Key nicht gefunden: {KEY_FILE}")
        print("   Erstelle einen Service Account in Google Cloud Console")
        print("   und speichere den JSON-Schlüssel als google-calendar-key.json")
        return None
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            KEY_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar Service verbunden")
        return service
    except Exception as e:
        print(f"❌ Fehler beim Verbinden: {e}")
        return None


def create_calendar_event(service, calendar_id, event_data):
    """
    Erstellt einen Kalender-Termin.
    
    Args:
        service: Google Calendar API Service
        calendar_id: ID des Kalenders (z.B. deine@gmail.com)
        event_data: Dict mit title, description, start_time, duration_minutes
    
    Returns:
        Event ID bei Erfolg, None bei Fehler
    """
    # Start und Ende berechnen
    if 'start_time' in event_data:
        start = datetime.fromisoformat(event_data['start_time'].replace('Z', '+00:00'))
    else:
        start = datetime.now() + timedelta(hours=1)
        start = start.replace(minute=0, second=0, microsecond=0)
    
    duration = event_data.get('duration_minutes', 30)
    end = start + timedelta(minutes=duration)
    
    # Event erstellen
    event = {
        'summary': event_data.get('title', 'Smart-Car Alert'),
        'description': event_data.get('description', ''),
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
        'colorId': '11' if 'DRINGEND' in event_data.get('title', '') else '9',  # Rot für kritisch, Blau normal
    }
    
    try:
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        print(f"✅ Termin erstellt: {event['summary']}")
        print(f"   Link: {created_event.get('htmlLink')}")
        return created_event['id']
    
    except Exception as e:
        print(f"❌ Fehler beim Erstellen: {e}")
        return None


def main():
    """Hauptfunktion - erstellt einen Test-Termin."""
    print("=" * 50)
    print("🚗 Smart-Car Google Calendar Integration")
    print("=" * 50)
    
    # Konfiguration laden
    config = load_config()
    if not config:
        return 1
    
    google_config = config.get('google_calendar', {})
    if not google_config.get('enabled', False):
        print("⚠️  Google Calendar ist deaktiviert in alerts.json")
        print("   Setze 'enabled': true um zu aktivieren")
        return 1
    
    calendar_id = google_config.get('calendar_id', '')
    if not calendar_id or calendar_id == 'DEINE_KALENDER_ID_HIER':
        print("❌ Keine Kalender-ID konfiguriert!")
        print("   Trage deine Gmail-Adresse oder Kalender-ID in alerts.json ein")
        return 1
    
    # Service erstellen
    service = get_calendar_service()
    if not service:
        return 1
    
    # Test-Event erstellen
    print("\n📅 Erstelle Test-Termin...")
    test_event = {
        'title': '🚗 TEST: Smart-Car Kalender funktioniert!',
        'description': 'Dies ist ein Test-Termin.\n\nDie Google Calendar Integration funktioniert korrekt!',
        'duration_minutes': 30
    }
    
    event_id = create_calendar_event(service, calendar_id, test_event)
    
    if event_id:
        print("\n✅ Integration funktioniert!")
        print("   Prüfe deinen Google Kalender für den Test-Termin.")
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
