from ai_filter import analyze_gov_initiative

def scrape_gov_initiatives():
    """
    Simulates monitoring government portals (DSIR, DPIIT, iDEX) for new R&D/hardware grants.
    In production, this would use pdfplumber for DSIR PDFs and Requests for DPIIT APIs.
    """
    print("[Gov] Checking DPIIT, iDEX, and DSIR portals for new updates...")
    leads = []
    
    # Simulated scraped raw data from government announcements
    raw_scraped_companies = [
        {
            "name": "Skyroot Aerospace", 
            "source": "iDEX Winner",
            "desc": "Awarded grant for developing indigenous cryogenic rocket engine subsystems and orbital launch vehicles.",
            "url": "https://idex.gov.in/winners/skyroot"
        },
        {
            "name": "FinPay Solutions", 
            "source": "DPIIT Startup India",
            "desc": "New UPI-based payment gateway focused on rural micro-finance.",
            "url": "https://www.startupindia.gov.in/content/sih/en/profile.Company.html"
        },
        {
            "name": "Zenith CNC Machines", 
            "source": "DSIR In-house R&D",
            "desc": "Recognized in-house R&D unit focusing on multi-axis CNC milling machines and automated tool changers.",
            "url": "https://dsir.gov.in/recognized_rd_units"
        }
    ]
    
    for raw_data in raw_scraped_companies:
        print(f"[Gov] Analyzing {raw_data['source']}: {raw_data['name']}")
        try:
            result = analyze_gov_initiative(raw_data['name'], raw_data['desc'])
            if result.get("is_relevant_for_mechanical_hiring"):
                print(f"  ✅ KEEP: {result.get('company_name')} ({result.get('classification')})")
                result["funnel_source"] = raw_data['source']
                result["source_link"] = raw_data.get("url", "https://idex.gov.in")
                leads.append(result)
            else:
                 print(f"  ❌ DROP: {result.get('company_name')}")
        except Exception as e:
            print(f"  [Error] analyzing gov lead: {e}")
            
    return leads
