#!/usr/bin/env python3
"""
Trip Processor Service fuer Smart-Car
Verarbeitet Fahrtdaten und erstellt Trip-Zusammenfassungen.
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

app = Flask(__name__)

# InfluxDB Konfiguration
INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'vehicle-admin-token')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', 'vehicle_org')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', 'vehicle_data')

# Aktive Fahrten im Speicher
active_trips = {}

def get_influx_client():
    """Erstellt InfluxDB Client."""
    return InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )


def query_trip_data(vehicle_id, start_time, end_time):
    """
    Holt alle GPS-Daten einer Fahrt aus InfluxDB.
    """
    client = get_influx_client()
    query_api = client.query_api()
    
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
        |> filter(fn: (r) => r["_measurement"] == "vehicle_gps")
        |> filter(fn: (r) => r["vehicle_id"] == "{vehicle_id}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"])
    '''
    
    try:
        tables = query_api.query(query)
        records = []
        for table in tables:
            for record in table.records:
                records.append({
                    'time': record.get_time(),
                    'latitude': record.values.get('latitude', 0),
                    'longitude': record.values.get('longitude', 0),
                    'speed_kmh': record.values.get('speed_kmh', 0)
                })
        return records
    except Exception as e:
        print(f"Query-Fehler: {e}")
        return []
    finally:
        client.close()


def calculate_trip_summary(vehicle_id, trip_id, gps_data):
    """
    Berechnet Trip-Zusammenfassung aus GPS-Daten.
    """
    if not gps_data or len(gps_data) < 2:
        return None
    
    # Zeitraum
    start_time = gps_data[0]['time']
    end_time = gps_data[-1]['time']
    duration_s = int((end_time - start_time).total_seconds())
    
    # Geschwindigkeitsanalyse
    speeds = [r['speed_kmh'] for r in gps_data if r['speed_kmh'] is not None]
    max_speed = max(speeds) if speeds else 0
    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    
    # Beschleunigung/Bremsung (aus Geschwindigkeitsaenderungen)
    accelerations = []
    decelerations = []
    
    for i in range(1, len(gps_data)):
        prev = gps_data[i-1]
        curr = gps_data[i]
        
        if prev['speed_kmh'] is not None and curr['speed_kmh'] is not None:
            time_diff = (curr['time'] - prev['time']).total_seconds()
            if time_diff > 0:
                speed_diff = curr['speed_kmh'] - prev['speed_kmh']
                acc = speed_diff / time_diff  # km/h/s
                
                if acc > 0:
                    accelerations.append(acc)
                elif acc < 0:
                    decelerations.append(abs(acc))
    
    max_acceleration = max(accelerations) if accelerations else 0
    max_braking = max(decelerations) if decelerations else 0
    
    # Ereignisse zaehlen (starke Beschleunigung/Bremsung)
    hard_accelerations = sum(1 for a in accelerations if a > 5)  # > 5 km/h/s
    hard_brakings = sum(1 for d in decelerations if d > 5)
    
    # Distanz schaetzen (vereinfacht aus Geschwindigkeit * Zeit)
    total_distance_km = 0
    for i in range(1, len(gps_data)):
        time_diff = (gps_data[i]['time'] - gps_data[i-1]['time']).total_seconds() / 3600
        avg_segment_speed = (gps_data[i]['speed_kmh'] + gps_data[i-1]['speed_kmh']) / 2
        total_distance_km += avg_segment_speed * time_diff
    
    # Fahrverhalten-Score (1-100)
    driving_score = 100
    driving_score -= min(30, hard_accelerations * 5)
    driving_score -= min(30, hard_brakings * 5)
    if max_speed > 130:
        driving_score -= 10
    if max_speed > 150:
        driving_score -= 10
    driving_score = max(0, driving_score)
    
    # Score-Bewertung
    if driving_score >= 80:
        driving_rating = 'Sehr gut'
    elif driving_score >= 60:
        driving_rating = 'Gut'
    elif driving_score >= 40:
        driving_rating = 'Maessig'
    else:
        driving_rating = 'Verbesserungswuerdig'
    
    return {
        'vehicle_id': vehicle_id,
        'trip_id': trip_id,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_s': duration_s,
        'duration_formatted': str(timedelta(seconds=duration_s)),
        'distance_km': round(total_distance_km, 2),
        'max_speed_kmh': round(max_speed, 1),
        'avg_speed_kmh': round(avg_speed, 1),
        'max_acceleration': round(max_acceleration, 2),
        'max_braking': round(max_braking, 2),
        'hard_accelerations': hard_accelerations,
        'hard_brakings': hard_brakings,
        'data_points': len(gps_data),
        'driving_score': driving_score,
        'driving_rating': driving_rating
    }


def save_trip_summary(summary):
    """
    Speichert Trip-Zusammenfassung in InfluxDB.
    """
    client = get_influx_client()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    try:
        line = (
            f'trip_summary,vehicle_id={summary["vehicle_id"]},trip_id={summary["trip_id"]} '
            f'duration_s={summary["duration_s"]}i,'
            f'distance_km={summary["distance_km"]},'
            f'max_speed_kmh={summary["max_speed_kmh"]},'
            f'avg_speed_kmh={summary["avg_speed_kmh"]},'
            f'max_acceleration={summary["max_acceleration"]},'
            f'max_braking={summary["max_braking"]},'
            f'hard_accelerations={summary["hard_accelerations"]}i,'
            f'hard_brakings={summary["hard_brakings"]}i,'
            f'driving_score={summary["driving_score"]}i'
        )
        
        write_api.write(bucket=INFLUXDB_BUCKET, record=line)
        print(f"Trip-Zusammenfassung gespeichert: {summary['trip_id']}")
        return True
    except Exception as e:
        print(f"Fehler beim Speichern: {e}")
        return False
    finally:
        client.close()


@app.route('/trip/start', methods=['POST'])
def trip_start():
    """
    POST /trip/start
    Body: {"vehicle_id": "VH001", "trip_id": "TRIP_001"}
    
    Startet eine neue Fahrt.
    """
    body = request.get_json() or {}
    vehicle_id = body.get('vehicle_id')
    trip_id = body.get('trip_id')
    
    if not vehicle_id or not trip_id:
        return jsonify({'error': 'vehicle_id und trip_id erforderlich'}), 400
    
    active_trips[trip_id] = {
        'vehicle_id': vehicle_id,
        'start_time': datetime.utcnow(),
        'status': 'active'
    }
    
    return jsonify({
        'status': 'started',
        'trip_id': trip_id,
        'vehicle_id': vehicle_id,
        'start_time': active_trips[trip_id]['start_time'].isoformat()
    })


@app.route('/trip/end', methods=['POST'])
def trip_end():
    """
    POST /trip/end
    Body: {"trip_id": "TRIP_001"}
    
    Beendet eine Fahrt und erstellt Zusammenfassung.
    """
    body = request.get_json() or {}
    trip_id = body.get('trip_id')
    
    if not trip_id:
        return jsonify({'error': 'trip_id erforderlich'}), 400
    
    if trip_id not in active_trips:
        return jsonify({'error': 'Fahrt nicht gefunden'}), 404
    
    trip = active_trips[trip_id]
    vehicle_id = trip['vehicle_id']
    start_time = trip['start_time']
    end_time = datetime.utcnow()
    
    # GPS-Daten abrufen
    gps_data = query_trip_data(vehicle_id, start_time, end_time)
    
    # Zusammenfassung berechnen
    summary = calculate_trip_summary(vehicle_id, trip_id, gps_data)
    
    if summary:
        # In InfluxDB speichern
        save_trip_summary(summary)
        
        # Aus aktiven Fahrten entfernen
        del active_trips[trip_id]
        
        return jsonify({
            'status': 'completed',
            'summary': summary
        })
    else:
        return jsonify({
            'status': 'completed',
            'warning': 'Keine GPS-Daten fuer Zusammenfassung vorhanden',
            'trip_id': trip_id
        })


@app.route('/trip/active', methods=['GET'])
def get_active_trips():
    """
    GET /trip/active
    Listet alle aktiven Fahrten.
    """
    trips = []
    for trip_id, data in active_trips.items():
        trips.append({
            'trip_id': trip_id,
            'vehicle_id': data['vehicle_id'],
            'start_time': data['start_time'].isoformat(),
            'duration_s': int((datetime.utcnow() - data['start_time']).total_seconds())
        })
    
    return jsonify({'active_trips': trips})


@app.route('/trip/history/<vehicle_id>', methods=['GET'])
def get_trip_history(vehicle_id):
    """
    GET /trip/history/VH001?days=7
    Holt Trip-Historie fuer ein Fahrzeug.
    """
    days = int(request.args.get('days', 7))
    
    client = get_influx_client()
    query_api = client.query_api()
    
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -{days}d)
        |> filter(fn: (r) => r["_measurement"] == "trip_summary")
        |> filter(fn: (r) => r["vehicle_id"] == "{vehicle_id}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: true)
    '''
    
    try:
        tables = query_api.query(query)
        trips = []
        for table in tables:
            for record in table.records:
                trips.append({
                    'time': record.get_time().isoformat(),
                    'trip_id': record.values.get('trip_id', ''),
                    'duration_s': record.values.get('duration_s', 0),
                    'distance_km': record.values.get('distance_km', 0),
                    'max_speed_kmh': record.values.get('max_speed_kmh', 0),
                    'driving_score': record.values.get('driving_score', 0)
                })
        
        return jsonify({
            'vehicle_id': vehicle_id,
            'days': days,
            'trips': trips,
            'total_trips': len(trips)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        client.close()


@app.route('/health', methods=['GET'])
def health():
    """Health Check Endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'trip-processor',
        'active_trips': len(active_trips)
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    print(f"Trip Processor startet auf Port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
