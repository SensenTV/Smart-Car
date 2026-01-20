import sqlite3
import os

# Pfad zur SQLite-Datei
db_path = "vehicle_data.db"

# Verbindung zur DB herstellen (erstellt Datei, falls sie noch nicht existiert)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tabellen erstellen
cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY,
    vehicle_code TEXT UNIQUE,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT,
    role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS error_codes (
    code TEXT PRIMARY KEY,
    description TEXT
)
""")

# Beispiel-Daten einfügen
cursor.executemany("""
INSERT OR IGNORE INTO error_codes (code, description) VALUES (?, ?)
""", [
    ('P0420', 'Katalysator Wirkungsgrad zu gering'),
    ('P0300', 'Zufällige Zylinderfehlzündung'),
    ('P0171', 'Gemisch zu mager (Bank 1)'),
    ('P0133', 'Sauerstoffsensor langsame Reaktion'),
])

# Änderungen speichern und DB schließen
conn.commit()
conn.close()

print(f"SQLite-Datenbank wurde erstellt: {db_path}")
