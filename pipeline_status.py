"""
Pipeline status tracker — writes live progress to a JSON file
that the dashboard UI polls every 2 seconds.
"""
import json
import os
import datetime

STATUS_FILE = os.path.join(os.path.dirname(__file__), "pipeline_status.json")

def _write(data):
    data["last_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def read_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"state": "idle", "message": "Pipeline has not run yet."}

def status_idle(message="Pipeline idle."):
    _write({"state": "idle", "message": message, "articles_scanned": 0, "matches_found": 0, "leads_added": 0})

def status_start():
    _write({
        "state": "running",
        "message": "Starting pipeline...",
        "current_feed": "",
        "current_article": "",
        "articles_scanned": 0,
        "matches_found": 0,
        "leads_added": 0,
        "errors": []
    })

def status_feed(feed_name):
    s = read_status()
    s["state"] = "running"
    s["current_feed"] = feed_name
    s["message"] = f"Fetching feed: {feed_name}"
    _write(s)

def status_article(feed_name, title, scanned):
    s = read_status()
    s["state"] = "running"
    s["current_feed"] = feed_name
    s["current_article"] = title[:80]
    s["articles_scanned"] = scanned
    s["message"] = f"[{feed_name}] Analyzing: {title[:60]}"
    _write(s)

def status_match(company, matches):
    s = read_status()
    s["matches_found"] = matches
    s["message"] = f"✅ Match found: {company}"
    _write(s)

def status_enriching(company):
    s = read_status()
    s["message"] = f"🔍 Enriching: {company} (Apollo/Hunter/Gemini)"
    _write(s)

def status_lead_added(company, total_added):
    s = read_status()
    s["leads_added"] = total_added
    s["message"] = f"✨ Added: {company} (#{total_added}/10 today)"
    _write(s)

def status_error(error_msg):
    s = read_status()
    errors = s.get("errors", [])
    errors.append(error_msg[:100])
    s["errors"] = errors[-5:]  # keep last 5
    _write(s)

def status_done(scanned, added):
    s = read_status()
    s["state"] = "done"
    s["message"] = f"Pipeline complete! Scanned {scanned} candidates, added {added} new leads."
    s["articles_scanned"] = scanned
    s["leads_added"] = added
    s["errors"] = []
    _write(s)

def status_quota_reached():
    s = read_status()
    s["state"] = "done"
    s["message"] = "🎯 Daily quota of 10 verified companies reached!"
    s["errors"] = []
    _write(s)
