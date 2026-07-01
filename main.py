import sys
import os

# Ensure the correct encoding for the terminal
sys.stdout.reconfigure(encoding='utf-8')

from database import init_db, insert_lead, count_extracted_leads_today, is_url_processed, mark_url_processed
from ingest_funding import scrape_funding_feeds
from ingest_exhibitions import scrape_exhibitions
from ingest_gov_initiatives import scrape_gov_initiatives
from ingest_patents import scrape_patents
from ingest_hackernews import scrape_hackernews
from ingest_hackaday import scrape_hackaday
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

    # 2. Gather Leads from Funnels
    leads = []
    
    print("\n--- PHASE 1: INGESTION ---")
    # Funding Funnel (Highest Priority)
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY"):
        funding_leads = scrape_funding_feeds()
        leads.extend(funding_leads)
    else:
        print("\n[Funding] Skipping Funding Funnel (API KEYS not set)")

    # Exhibition Funnel
    exhibition_leads = scrape_exhibitions()
    leads.extend(exhibition_leads)
    
    # Government Initiatives Funnel (DSIR, iDEX, DPIIT)
    gov_leads = scrape_gov_initiatives()
    leads.extend(gov_leads)
    
    # Patents Funnel
    patent_leads = scrape_patents()
    leads.extend(patent_leads)
        
    # Hackaday Funnel
    hd_leads = scrape_hackaday()
    leads.extend(hd_leads)
    
    # HackerNews Funnel (Lowest Priority due to early-stage/stealth nature)
    hn_leads = scrape_hackernews()
    leads.extend(hn_leads)
    
    # Prioritize leads by source reliability
    funnel_priority = {
        "Funding RSS": 1,
        "Exhibitions": 2,
        "Government Initiatives": 3,
        "Patents": 4,
        "Hackaday": 5,
        "HackerNews": 6
    }
    leads.sort(key=lambda x: funnel_priority.get(x.get('funnel_source', ''), 10))
    
    # 3. Process, Enrich and Store
    print(f"\n--- PHASE 2: ENRICHMENT & STORAGE ({len(leads)} raw candidate leads) ---")
    
    new_leads_added = 0
    for lead in leads:
        # Check quota at start of each iteration
        if count_extracted_leads_today() >= 10:
            print("\n[Quota Enforcer] 🎯 Reached daily limit of 10 verified extracted leads! Stopping enrichment loop.")
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
            
        print(f"\n🔍 Processing Candidate: {company} (Source: {lead.get('funnel_source', 'Unknown')})")
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
            enrichment_source=contact_data.get("enrichment_source", "OSINT API")
        )
        
        if inserted:
            print(f"✨ ADDED VERIFIED LEAD (#{count_extracted_leads_today()}/10 today): {company} | Emails: {contact_data['emails']}")
            new_leads_added += 1
        else:
            print(f"🔄 DUPLICATE LEAD: {company} (Already in database)")

    print("\n==========================================================")
    print(f" Pipeline Complete! Added {new_leads_added} new verified companies.")
    print(f" Total verified leads today: {count_extracted_leads_today()} / 10")
    print("==========================================================")

if __name__ == "__main__":
    main()

