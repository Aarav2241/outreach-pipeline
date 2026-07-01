import sys
import os
import socket

# Prevent infinite hanging on slow RSS feeds or API connections
socket.setdefaulttimeout(15)

# Ensure the correct encoding for the terminal
sys.stdout.reconfigure(encoding='utf-8')

from database import init_db, insert_lead, count_extracted_leads_today
from ingest_funding import scrape_funding_feeds
from contact_enrichment import enrich_contact
from pipeline_status import status_start, status_done, status_quota_reached, status_enriching, status_lead_added, status_error

LOCK_FILE = os.path.join(os.path.dirname(__file__), "pipeline.lock")

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                print(f"[Lock Error] Another pipeline instance (PID {pid}) is already running! Exiting immediately.")
                return False
            except OSError:
                pass  # Stale lock from dead process, safe to overwrite
        except Exception:
            pass
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    return True

def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

def main():
    if not acquire_lock():
        return
    try:
        print("==========================================================")
        print(" GTM Automated Signal Engine - IITB Mechanical Pipeline   ")
        print("==========================================================\n")
        
        # 1. Initialize Database & Check Daily Quota
        init_db()
        status_start()
        
        current_today_count = count_extracted_leads_today()
        print(f"[Quota Enforcer] Current verified extracted leads added today: {current_today_count} / 10")
        if current_today_count >= 10:
            print("[Quota Enforcer] 🎯 Daily quota of 10 verified companies reached! Exiting early to conserve API credits.")
            status_quota_reached()
            return

    # 2. Stream leads: scrape → filter → enrich → store (each lead flows through immediately)
    print("\n--- STREAMING PIPELINE: Scrape → AI Filter → Enrich → Store ---")
    print("    (Leads appear on the dashboard as soon as each one is processed)\n")
    
    new_leads_added = 0
    candidates_seen = 0
    
    for lead in scrape_funding_feeds():
        candidates_seen += 1
        
        # Check quota at start of each iteration
        if count_extracted_leads_today() >= 10:
            print("\n[Quota Enforcer] 🎯 Reached daily limit of 10 verified extracted leads! Stopping.")
            status_quota_reached()
            break

        company = lead.get('company_name', '').strip()
        if not company or company.lower() in ["none", "not specified", "unknown"]:
            print(f"❌ DROPPING INVALID COMPANY NAME: {company}")
            continue
            
        print(f"\n🔍 Enriching: {company} (Source: {lead.get('funnel_source', 'Unknown')})")
        status_enriching(company)
        contact_data = enrich_contact(company, lead.get('funnel_source', 'Unknown'), lead.get('key_technology', 'Unknown'))
        
        if not contact_data or not contact_data.get("emails") or contact_data.get("emails") == "N/A":
            print(f"❌ DROPPING LEAD: {company} (No extracted emails found)")
            continue
        
        firmographics = contact_data.get("firmographics", {})
        
        inserted = insert_lead(
            company_name=company,
            funnel_source=lead.get('funnel_source', 'Unknown'),
            classification=lead.get('classification', 'Unknown'),
            key_technology=lead.get('key_technology', 'Unknown'),
            justification=lead.get('justification', 'N/A'),
            contact_emails=contact_data["emails"],
            linkedin_url=contact_data["linkedin_url"],
            email_pattern=contact_data.get("email_pattern"),
            company_age=firmographics.get("founded_year", lead.get("company_age", "Unknown")),
            company_type=firmographics.get("sector", lead.get("company_type", "Unknown")),
            global_presence=firmographics.get("employee_count", lead.get("global_presence", "Unknown")),
            enrichment_source=contact_data.get("enrichment_source", "OSINT API"),
            source_link=lead.get("source_link", "N/A")
        )
        
        if inserted:
            new_leads_added += 1
            print(f"✨ ADDED LEAD #{count_extracted_leads_today()}/10 → {company} | Emails: {contact_data['emails']}")
            status_lead_added(company, count_extracted_leads_today())
        else:
            print(f"🔄 DUPLICATE: {company} (Already in database)")

    print("\n==========================================================")
    print(f" Pipeline Complete! Scanned {candidates_seen} candidates, added {new_leads_added} new verified companies.")
    print(f" Total verified leads today: {count_extracted_leads_today()} / 10")
    print("==========================================================")
    status_done(candidates_seen, new_leads_added)
    release_lock()

if __name__ == "__main__":
    main()
