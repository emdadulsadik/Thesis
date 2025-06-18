# processor.py
import sys
import json
import sqlite3

# Create SQLite DB
conn = sqlite3.connect("telemetry.db")
c = conn.cursor()
c.execute(
    '''
        CREATE TABLE IF NOT EXISTS telemetry (
            timestamp REAL, machine_id TEXT, temperature REAL, vibration REAL, load REAL
        )
    '''
)

for line in sys.stdin:
    try:
        data = json.loads(line)
        c.execute("INSERT INTO telemetry VALUES (?, ?, ?, ?, ?)", 
                  (data['timestamp'], data['machine_id'], data['temperature'], data['vibration'], data['load']))
        conn.commit()
        print(f"Processed data for {data['machine_id']}")
    except Exception as e:
        print("Error processing:", e)
