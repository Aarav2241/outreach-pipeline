import urllib.request
import urllib.parse
import os
import json
from config import HUNTER_API_KEY, CONTACTOUT_API_KEY, SIGNALHIRE_API_KEY, KENDO_API_KEY, GEMINI_API_KEY, TEST_MODE
from google import genai
from google.genai import types
from ai_filter import call_groq, call_openrouter

# Setup Gemini for generating the personalized LinkedIn Pitch
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
        # Common heuristics
        if '.' in local_part:
            return f"{{first}}.{{last}}@{domain}"
        elif len(local_part) > 3 and local_part.isalpha():
            # Could be {first} or {first}{last}
            return f"{{first}}@{domain} OR {{first}}{{last}}@{domain}"
    return f"unknown_pattern@{domain}"

def guess_founder_emails(company_name, domain, pattern):
    """Uses LLM to guess key personnel names and construct their emails."""
    prompt = f"Identify up to 2 key people at the company '{company_name}' who handle hiring, leadership, or engineering (e.g., Founders, CEO, Talent Acquisition, HR Head, VP of Engineering, Business Development). Return their full names in a strict JSON list format like {{\"names\": [\"First Last\", \"First Last\"]}}. If you absolutely don't know, return an empty list."
    system = "You are a helpful data enrichment assistant. Only return valid JSON with the key 'names'. Do not wrap in markdown."
    names = []
    try:
        res = call_groq(system, prompt)
        names = res.get("names", [])
    except Exception as e:
        print(f"      [LLM Name Guess Error Groq]: {e}")
        try:
             res = call_openrouter(system, prompt)
             names = res.get("names", [])
        except Exception as e2:
             print(f"      [LLM Name Guess Error OpenRouter]: {e2}")
             
    emails = []
    for name in names:
        parts = name.strip().split()
        if len(parts) >= 2:
            first = parts[0].lower().replace(".", "").replace(",", "")
            last = parts[-1].lower().replace(".", "").replace(",", "")
            
            if pattern and pattern != f"unknown_pattern@{domain}":
                p = pattern.split(" OR ")[0]
                e = p.replace("{first}", first).replace("{last}", last)
                emails.append(f"{name} -> {e}")
            else:
                emails.append(f"{name} -> {first}.{last}@{domain}")
                emails.append(f"{name} -> {first}@{domain}")
    
    if not emails:
        emails = [f"founders@{domain}", f"info@{domain}"]
        
    return emails

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
    # Fallback heuristic
    return company_name.lower().replace(" ", "").replace(",", "") + ".com"

def generate_linkedin_pitch(company_name, source, tech):
    """Uses Gemini to generate a personalized 300-char LinkedIn connection request."""
    if not client:
        return "Hi [Name], I'm with IIT Bombay's Placement Office. Would love to connect regarding hiring top mechanical engineering talent."
        
    prompt = f"Write a 280-character LinkedIn connection request to the Founder/VP Engineering of '{company_name}'. Mention you saw them via '{source}' and noted their work in '{tech}'. Introduce IIT Bombay's mechanical talent. Be professional but conversational."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Pitch Error]: {e}")
        return "Hi, reaching out from IIT Bombay Placement Office to connect regarding mechanical engineering hiring."

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
    Finds contact info using the API Waterfall.
    No longer generates personalized pitches per user request.
    """
    domain = get_real_domain(company_name)
    linkedin_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote('\"' + company_name + '\" founder OR engineering')}"
    
    if TEST_MODE:
        print("    -> [TEST MODE] Bypassing contact APIs.")
        return {
            "emails": f"test@{domain}",
            "linkedin_url": linkedin_url,
            "linkedin_pitch": "N/A - Feature Disabled",
            "email_pattern": f"{{first}}.{{last}}@{domain}"
        }
    
    found_emails = None
    
    extracted_emails = query_hunter(domain)
    if not extracted_emails:
        extracted_emails = query_contactout(domain)
    if not extracted_emails:
        extracted_emails = query_signalhire(domain)
    if not extracted_emails:
        extracted_emails = query_kendo(domain)
        
    extracted_emails = extracted_emails or []
    # Deduplicate and limit to 4
    extracted_emails = list(dict.fromkeys(extracted_emails))[:4]

    # Extract pattern (before modifying strings)
    email_pattern = extract_email_pattern(extracted_emails, domain)
    
    # Always try to estimate founders
    print("    -> Using LLM to guess/estimate founder emails.")
    estimated_emails = guess_founder_emails(company_name, domain, email_pattern)
    
    # Deduplicate estimated against extracted
    extracted_raw_set = set()
    for e in extracted_emails:
        if "->" in e:
            extracted_raw_set.add(e.split("->")[-1].strip().lower())
        else:
            extracted_raw_set.add(e.strip().lower())

    filtered_estimated = []
    for e in estimated_emails:
        raw_e = e.split("->")[-1].strip().lower() if "->" in e else e.strip().lower()
        if raw_e not in extracted_raw_set:
            filtered_estimated.append(e)

    # Add status tags
    tagged_extracted = [e + " (Extracted)" for e in extracted_emails]
    tagged_estimated = [e + " (Estimated)" for e in filtered_estimated]
    
    final_emails = tagged_extracted + tagged_estimated
    
    return {
        "emails": ", ".join(final_emails) if final_emails else "N/A",
        "linkedin_url": linkedin_url,
        "email_pattern": email_pattern
    }
