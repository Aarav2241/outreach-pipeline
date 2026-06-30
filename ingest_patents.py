from ai_filter import analyze_patent
import time

def scrape_patents():
    """
    Simulates querying a patent database (like Google Patents or EPO API)
    for companies filing >= 5 patents in mechanical/hardware IPC classes.
    """
    print("[Patents] Querying patent databases for high-volume hardware filers...")
    leads = []
    
    # Simulated scraped raw data from a patent database
    raw_scraped_companies = [
        {
            "name": "GreyOrange Robotics", 
            "patent_count": 12,
            "desc": "System and method for automated warehousing using mobile robotic drive units and storage racks."
        },
        {
            "name": "Ola Electric Mobility", 
            "patent_count": 8,
            "desc": "Thermal management system and structural battery pack for two-wheeled electric vehicles."
        },
        {
            "name": "Infosys", 
            "patent_count": 45,
            "desc": "Method and system for generating distributed ledger networks using block-chain technology."
        }
    ]
    
    for raw_data in raw_scraped_companies:
        # Proceeding with all filers regardless of volume
            
        print(f"[Patents] Analyzing Filer: {raw_data['name']} ({raw_data['patent_count']} patents)")
        try:
            result = analyze_patent(raw_data['name'], raw_data['desc'])
            if result.get("is_relevant_for_mechanical_hiring"):
                print(f"  ✅ KEEP: {result.get('company_name')} ({result.get('classification')})")
                result["funnel_source"] = "Patent Filings"
                leads.append(result)
            else:
                 print(f"  ❌ DROP: {result.get('company_name')}")
        except Exception as e:
            print(f"  [Error] analyzing patent lead: {e}")
            
    return leads
