import sys
import os

# Ensure the correct encoding for the terminal
sys.stdout.reconfigure(encoding='utf-8')

from database import init_db, insert_lead
from ingest_funding import scrape_funding_feeds
from ingest_exhibitions import scrape_exhibitions
from ingest_gov_initiatives import scrape_gov_initiatives
from ingest_patents import scrape_patents
from ingest_hackernews import scrape_hackernews
from ingest_hackaday import scrape_hackaday
from contact_enrichment import enrich_contact

def main():
    print("==================================================")
    print(" IITB Mechanical Intelligence Pipeline Initiated ")
    print("==================================================\n")
    
    # 1. Initialize Database
    init_db()
    
    # 2. Gather Leads from Funnels
    leads = []
    
    print("\n--- PHASE 1: INGESTION ---")
    # Exhibition Funnel
    exhibition_leads = scrape_exhibitions()
    leads.extend(exhibition_leads)
    
    # Government Initiatives Funnel (DSIR, iDEX, DPIIT)
    gov_leads = scrape_gov_initiatives()
    leads.extend(gov_leads)
    
    # Patents Funnel
    patent_leads = scrape_patents()
    leads.extend(patent_leads)
    
    # Funding Funnel
    # Uncomment below to run real funding RSS feeds (requires Gemini API Key)
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY"):
        funding_leads = scrape_funding_feeds()
        leads.extend(funding_leads)
    else:
        print("\n[Funding] Skipping Funding Funnel (API KEYS not set)")
        
    # HackerNews Funnel
    hn_leads = scrape_hackernews()
    leads.extend(hn_leads)
    
    # Hackaday Funnel
    hd_leads = scrape_hackaday()
    leads.extend(hd_leads)
    
    # 3. Process, Enrich and Store
    print(f"\n--- PHASE 2: ENRICHMENT & STORAGE ({len(leads)} valid leads) ---")
    
    new_leads_added = 0
    for lead in leads:
        company = lead.get('company_name', '').strip()
        if not company or company.lower() in ["none", "not specified", "unknown"]:
            print(f"❌ DROPPING INVALID COMPANY NAME: {company}")
            continue
            
        contact_data = enrich_contact(company, lead.get('funnel_source', 'Unknown'), lead.get('key_technology', 'Unknown'))
        
        inserted = insert_lead(
            company_name=company,
            funnel_source=lead.get('funnel_source', 'Unknown'),
            classification=lead.get('classification', 'Unknown'),
            key_technology=lead.get('key_technology', 'Unknown'),
            justification=lead.get('justification', 'N/A'),
            contact_emails=contact_data["emails"],
            linkedin_url=contact_data["linkedin_url"],
            email_pattern=contact_data.get("email_pattern"),
            company_age=lead.get("company_age", "Unknown"),
            company_type=lead.get("company_type", "Unknown"),
            global_presence=lead.get("global_presence", "Unknown")
        )
        
        if inserted:
            print(f"✨ ADDED NEW LEAD: {company} | Emails: {contact_data['emails']}")
            new_leads_added += 1
        
        if not inserted:
            print(f"🔄 DUPLICATE LEAD: {company} (Already in database)")

    print("\n==================================================")
    print(f" Pipeline Complete! Added {new_leads_added} new companies to the database.")
    print("==================================================")

if __name__ == "__main__":
    main()
