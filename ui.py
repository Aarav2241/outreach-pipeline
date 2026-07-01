from flask import Flask, render_template, jsonify
import sqlite3
import subprocess
import sys
import datetime
from config import DB_PATH
from database import init_db
from scheduler import start_scheduler
from pipeline_status import read_status

app = Flask(__name__)

def get_last_refresh_time():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date_added) FROM leads")
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        try:
            dt = datetime.datetime.fromisoformat(row[0])
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(row[0])[:19]
    return "Never"

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
    return render_template('index.html', leads=leads, last_refresh=get_last_refresh_time())

@app.route('/sync', methods=['POST'])
def sync_leads():
    log_file = open("pipeline.log", "a", encoding="utf-8")
    subprocess.Popen([sys.executable, "main.py"], stdout=log_file, stderr=log_file)
    return jsonify({"status": "Started pipeline in background", "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

@app.route('/pipeline-status')
def pipeline_status():
    """Returns live pipeline status as JSON for the dashboard status bar."""
    return jsonify(read_status())

@app.route('/clear', methods=['POST'])
def clear_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM leads')
    cursor.execute('DELETE FROM processed_urls')
    conn.commit()
    conn.close()
    return jsonify({"status": "Cleared all old leads from database."})

if __name__ == '__main__':
    print(f"Ensuring database exists...")
    init_db()
    print(f"Starting APScheduler daemon...")
    start_scheduler(interval_hours=6)
    print(f"Starting dashboard...")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
