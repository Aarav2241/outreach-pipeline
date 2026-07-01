import sys
import os
import socket

# Prevent infinite hanging on slow RSS feeds or API connections
socket.setdefaulttimeout(15)

# Ensure the correct encoding for the terminal
sys.stdout.reconfigure(encoding='utf-8')

from database import init_db, insert_lead, count_extracted_leads_today, is_url_processed, mark_url_processed
from ingest_funding import scrape_funding_feeds
from contact_enrichment import enrich_contact

def main():
    print("==========================================================")
    print(" GTM Automated Signal Engine - IITB Mechanical Pipeline   ")
    print("==========================================================\n")
    
    # 1. Initialize Database & Check Daily Quota
    init_db()
    
    current_today_count = count_extracted_leads_today()
    print(f"[Quota Enforcer] Current verified extracted leads added today: {current_today_count} / 10")
    if current_today_count >= 10:
        print("[Quota Enforcer] 🎯 Daily quota of 10 verified companies reached! Exiting early to conserve API credits.")
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
            break

        company = lead.get('company_name', '').strip()
        if not company or company.lower() in ["none", "not specified", "unknown"]:
            print(f"❌ DROPPING INVALID COMPANY NAME: {company}")
            continue
            
        # Deduplication check
        dedup_key = lead.get('url') or company
        if is_url_processed(dedup_key):
            print(f"⏭️ [Dedup Guard] Skipping already processed item: {company}")
            continue
        mark_url_processed(dedup_key)
            
        print(f"\n🔍 Enriching: {company} (Source: {lead.get('funnel_source', 'Unknown')})")
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
        else:
            print(f"🔄 DUPLICATE: {company} (Already in database)")

    print("\n==========================================================")
    print(f" Pipeline Complete! Scanned {candidates_seen} candidates, added {new_leads_added} new verified companies.")
    print(f" Total verified leads today: {count_extracted_leads_today()} / 10")
    print("==========================================================")

if __name__ == "__main__":
    main()
