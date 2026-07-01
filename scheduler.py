import subprocess
import sys
import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler

last_refresh_time = "Never"

def run_pipeline_job():
    global last_refresh_time
    print(f"\n[Scheduler] Triggering GTM Automated Signal Engine pipeline at {datetime.datetime.now()}...")
    try:
        log_file = open("pipeline.log", "a", encoding="utf-8")
        subprocess.Popen([sys.executable, "main.py"], stdout=log_file, stderr=log_file)
        last_refresh_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"[Scheduler Error]: {e}")

def start_scheduler(interval_hours=6):
    """Starts the APScheduler background daemon."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_pipeline_job, 'interval', hours=interval_hours)
    scheduler.start()
    print(f"[Scheduler] Background scheduler started. Running pipeline every {interval_hours} hours.")
    return scheduler

if __name__ == "__main__":
    print("[Scheduler] Running in standalone mode. Press Ctrl+C to exit.")
    run_pipeline_job()
    start_scheduler(interval_hours=6)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("[Scheduler] Shutting down.")
