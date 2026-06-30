from flask import Flask, render_template, jsonify
import sqlite3
import subprocess
import datetime
import threading
import time
from config import DB_PATH
from database import init_db

app = Flask(__name__)
last_refresh_time = "Never"

def get_all_leads():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads ORDER BY date_added DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.route('/')
def index():
    leads = get_all_leads()
    return render_template('index.html', leads=leads, last_refresh=last_refresh_time)

@app.route('/sync', methods=['POST'])
def sync_leads():
    global last_refresh_time
    subprocess.Popen(["python", "main.py"])
    last_refresh_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({"status": "Started pipeline in background", "time": last_refresh_time})

def auto_sync_loop():
    global last_refresh_time
    while True:
        # Sleep 30 minutes (1800 seconds)
        time.sleep(1800)
        print("[Auto-Sync] Waking up to sync pipeline...")
        subprocess.Popen(["python", "main.py"])
        last_refresh_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == '__main__':
    print(f"Ensuring database exists...")
    init_db()
    print(f"Starting auto-sync daemon...")
    threading.Thread(target=auto_sync_loop, daemon=True).start()
    print(f"Starting dashboard...")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
