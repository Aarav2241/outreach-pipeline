import urllib.request
import urllib.parse
import os
import json
from config import HUNTER_API_KEY, CONTACTOUT_API_KEY, SIGNALHIRE_API_KEY, KENDO_API_KEY, APOLLO_API_KEY, GEMINI_API_KEY, TEST_MODE
from google import genai
from google.genai import types
from database import get_cached_profile, save_cached_profile

# Setup Gemini for generating pitches if needed
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

def extract_email_pattern(emails, domain):
    """Deduces the corporate email pattern from a list of emails."""
    if not emails: return None
    for email in emails:
        if "->" in email:
            email = email.split("->")[-1].strip()
        local_part = email.split('@')[0].lower()
        if '.' in local_part:
            return f"{{first}}.{{last}}@{domain}"
        elif len(local_part) > 3 and local_part.isalpha():
            return f"{{first}}@{domain} OR {{first}}{{last}}@{domain}"
    return f"unknown_pattern@{domain}"

def get_real_domain(company_name):
    """Uses Clearbit free API to get the true corporate domain."""
    url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={urllib.parse.quote(company_name)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get('domain')
    except Exception:
        pass
    return company_name.lower().replace(" ", "").replace(",", "") + ".com"

def query_apollo_org(domain, company_name):
    """Queries Apollo.io organization enrichment API for firmographics."""
    print(f"    -> Trying Apollo.io API for firmographics...")
    if not APOLLO_API_KEY or APOLLO_API_KEY == "your_apollo_api_key_here":
        return {}
    url = "https://api.apollo.io/v1/organizations/enrich"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY
    }
    data = {"domain": domain} if domain else {"name": company_name}
    try:
        req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode('utf-8'), method='POST')
        with urllib.request.urlopen(req) as response:
            res_json = json.loads(response.read())
            org = res_json.get("organization", {})
            if not org:
                return {}
            return {
                "employee_count": str(org.get("estimated_num_employees", "Unknown")),
                "revenue_range": str(org.get("annual_revenue_printed", "Unknown")),
                "sector": str(org.get("industry", "Mechanical / DeepTech")),
                "founded_year": str(org.get("founded_year", "Unknown")),
                "funding_raised": str(org.get("total_funding_printed", "Unknown"))
            }
    except Exception as e:
        print(f"    -> Apollo API Failed: {e}")
        return {}

def query_hunter(domain):
    print(f"    -> Trying Hunter.io...")
    if not HUNTER_API_KEY: return None
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            emails = []
            for e in data.get('data', {}).get('emails', [])[:4]:
                name = f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()
                position = e.get('position', 'Employee')
                email_val = e.get('value', '')
                if name:
                    emails.append(f"{name} ({position}) -> {email_val}")
                else:
                    emails.append(email_val)
            return emails if emails else None
    except Exception as e:
        print(f"    -> Hunter API Failed/Empty: {e}")
        return None

def query_contactout(domain):
    print(f"    -> Trying ContactOut...")
    if not CONTACTOUT_API_KEY: return None
    url = f"https://api.contactout.com/v1/email/find?domain={domain}"
    headers = {"Authorization": f"Basic {CONTACTOUT_API_KEY}", "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            emails = [data.get('email')] if data.get('email') else []
            return emails if emails else None
    except Exception as e:
        print(f"    -> ContactOut API Failed: {e}")
        return None

def query_signalhire(domain):
    print(f"    -> Trying SignalHire...")
    if not SIGNALHIRE_API_KEY: return None
    url = f"https://www.signalhire.com/api/v1/candidate/search"
    headers = {"apikey": SIGNALHIRE_API_KEY, "Content-Type": "application/json"}
    data = {"domain": domain}
    try:
        req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode('utf-8'))
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            emails = [e.get('email') for e in data.get('candidates', []) if e.get('email')][:2]
            return emails if emails else None
    except Exception as e:
        print(f"    -> SignalHire API Failed: {e}")
        return None

def query_kendo(domain):
    print(f"    -> Trying Kendo...")
    if not KENDO_API_KEY: return None
    url = f"https://kendoemailapp.com/api/v1/find?domain={domain}&apikey={KENDO_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            emails = [e['email'] for e in data.get('emails', [])][:2]
            return emails if emails else None
    except Exception as e:
        print(f"    -> Kendo API Failed: {e}")
        return None

def enrich_contact(company_name, funnel_source, key_tech):
    """
    Finds contact info using the API Waterfall and Apollo Org Enrichment.
    Enforces strict extracted-only email policy per user request.
    """
    domain = get_real_domain(company_name)
    linkedin_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote('\"' + company_name + '\" founder OR engineering')}"
    
    if TEST_MODE:
        print("    -> [TEST MODE] Bypassing contact APIs.")
        return {
            "emails": f"test.founder@{domain} (Extracted)",
            "linkedin_url": linkedin_url,
            "email_pattern": f"{{first}}.{{last}}@{domain}",
            "firmographics": {},
            "enrichment_source": "Test Mode"
        }
    
    extracted_emails = query_hunter(domain)
    if not extracted_emails:
        extracted_emails = query_contactout(domain)
    if not extracted_emails:
        extracted_emails = query_signalhire(domain)
    if not extracted_emails:
        extracted_emails = query_kendo(domain)
        
    extracted_emails = extracted_emails or []
    extracted_emails = list(dict.fromkeys(extracted_emails))[:4]

    # Enforce Extracted-Only Policy: Drop if 0 emails extracted
    if not extracted_emails:
        print(f"    ❌ No extracted emails found for {company_name}. Dropping lead (estimation disabled).")
        return None

    email_pattern = extract_email_pattern(extracted_emails, domain)
    tagged_extracted = [e + " (Extracted)" for e in extracted_emails]
    
    # 3-Tier Firmographic Caching & Enrichment
    cached_org = get_cached_profile(company_name)
    if cached_org and cached_org.get("enrichment_source") != "Cache":
        print(f"    ⚡ [Cache Hit] Loaded firmographics from SQLite cache.")
        firmographics = cached_org
        enrichment_source = "Cache"
    else:
        firmographics = query_apollo_org(domain, company_name)
        enrichment_source = "Apollo API" if firmographics else "OSINT API"
        save_cached_profile(
            name=company_name,
            domain=domain,
            employee_count=firmographics.get("employee_count", "Unknown"),
            revenue_range=firmographics.get("revenue_range", "Unknown"),
            sector=firmographics.get("sector", "Mechanical / DeepTech"),
            founded_year=firmographics.get("founded_year", "Unknown"),
            funding_raised=firmographics.get("funding_raised", "Unknown"),
            enrichment_source=enrichment_source
        )
    
    return {
        "emails": ", ".join(tagged_extracted),
        "linkedin_url": linkedin_url,
        "email_pattern": email_pattern,
        "firmographics": firmographics,
        "enrichment_source": enrichment_source
    }
