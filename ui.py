from flask import Flask, render_template, jsonify
import sqlite3
import subprocess
import sys
import datetime
from config import DB_PATH
from database import init_db, count_extracted_leads_today
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

def is_scraper_running():
    try:
        res = subprocess.run(["pgrep", "-f", "main.py"], stdout=subprocess.PIPE, text=True)
        pids = [p.strip() for p in res.stdout.strip().split() if p.strip().isdigit() and int(p.strip()) != os.getpid()]
        if len(pids) > 0:
            return True
    except Exception:
        pass

    lock_file = os.path.join(os.path.dirname(__file__), "pipeline.lock")
    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())
            cmdline_file = f"/proc/{pid}/cmdline"
            if os.path.exists(cmdline_file):
                with open(cmdline_file, "rb") as f:
                    cmd = f.read().decode('utf-8', errors='ignore')
                if "main.py" not in cmd:
                    try: os.remove(lock_file)
                    except Exception: pass
                    return False
                return True
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            try: os.remove(lock_file)
            except Exception: pass
    return False

@app.route('/sync', methods=['POST'])
def sync_leads():
    if is_scraper_running():
        return jsonify({"status": "⚠️ Pipeline is already running in the background! Please wait for it to finish.", "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    if count_extracted_leads_today() >= 10:
        return jsonify({"status": "🎯 Daily quota of 10 verified companies already reached today! Use 'Clear Old Leads' if you want to test again.", "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
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
