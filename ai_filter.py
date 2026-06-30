import os
import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, TEST_MODE
from groq import Groq
import requests

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

def call_groq(system_instruction, prompt):
    client = Groq(api_key=GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)

def call_openrouter(system_instruction, prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "OutreachPipeline"
    }
    data = {
        "model": "meta-llama/llama-3-8b-instruct",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    res = response.json()
    return json.loads(res['choices'][0]['message']['content'])

def llm_waterfall(system_instruction, prompt, schema):
    """Tries Gemini, then Groq, then OpenRouter."""
    
    # Append schema to system instruction for Groq/OpenRouter
    schema_str = f"\n\nCRITICAL: You must return a valid JSON object strictly matching this schema structure. Do not return markdown, only the raw JSON. Keys required: {list(schema['properties'].keys())}"
    system_instruction_appended = system_instruction + schema_str

    try:
        if client:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=types.Schema(**schema)
                )
            )
            return json.loads(response.text)
    except Exception as e:
        print(f"      [LLM] Gemini Failed: {e}. Trying Groq...")
    
    try:
        return call_groq(system_instruction_appended, prompt)
    except Exception as e:
        print(f"      [LLM] Groq Failed: {e}. Trying OpenRouter...")
        
    try:
        return call_openrouter(system_instruction_appended, prompt)
    except Exception as e:
        print(f"      [LLM] OpenRouter Failed: {e}")
        return None

# ---------------------------------------------------------
# PROMPT 1: FUNDING NEWS CLASSIFICATION
# ---------------------------------------------------------
FUNDING_SYSTEM_INSTRUCTION = """
You are an expert venture capital analyst specializing in deeptech, manufacturing, and hardware startups.
Your task is to analyze a news article summary about a startup funding event and classify the startup.

Definitions:
- Hardware/Mechanical Startup: A company primarily building physical products (e.g., robotics, EVs, aerospace, IoT devices, battery tech, automation machinery).
- Deeptech Startup: A company based on significant scientific breakthroughs or difficult-to-replicate physical IP.
- Neither/Software: A company building SaaS, consumer apps, fintech, edtech, e-commerce, or generic software.

Instructions:
1. Determine if the startup qualifies as "Hardware", "Deeptech", "Both", or "Neither/Software".
2. Provide a 1-sentence justification based on the text.
3. Extract the startup's name.
4. Extract the primary product or technology mentioned.
5. If the startup is "Neither/Software", set is_relevant_for_mechanical_hiring to false.
"""

def analyze_funding_news(title, summary):
    if TEST_MODE:
        return {
            "company_name": "Test Company",
            "classification": "Hardware",
            "justification": "Simulated hardware company.",
            "key_technology": "Robotics",
            "is_relevant_for_mechanical_hiring": True,
            "company_age": "Unknown",
            "company_type": "Unknown",
            "global_presence": "Unknown"
        }
    
    prompt = f"Article Title: {title}\nArticle Summary: {summary}\n"
    schema = {
        "type": types.Type.OBJECT,
        "properties": {
            "company_name": types.Schema(type=types.Type.STRING),
            "classification": types.Schema(type=types.Type.STRING, enum=["Hardware", "Deeptech", "Both", "Neither/Software"]),
            "justification": types.Schema(type=types.Type.STRING),
            "key_technology": types.Schema(type=types.Type.STRING),
            "is_relevant_for_mechanical_hiring": types.Schema(type=types.Type.BOOLEAN),
            "company_age": types.Schema(type=types.Type.STRING, description="Estimate age or return 'Unknown'"),
            "company_type": types.Schema(type=types.Type.STRING, description="MNC/Listed/Startup or 'Unknown'"),
            "global_presence": types.Schema(type=types.Type.STRING, description="Countries or 'Unknown'")
        },
        "required": ["company_name", "classification", "justification", "key_technology", "is_relevant_for_mechanical_hiring"]
    }
    
    return llm_waterfall(FUNDING_SYSTEM_INSTRUCTION, prompt, schema)

# Negative keywords to instantly drop without hitting LLM
NEGATIVE_KEYWORDS = [
    "saas", "software as a service", "cloud computing", 
    "cybersecurity", "cyber security", "web3", "blockchain", 
    "crypto", "nft", "fintech", "adtech", "talent platform"
]

def pre_filter_fails(description):
    """Returns True if the description contains instant-drop negative keywords."""
    desc_lower = description.lower()
    for kw in NEGATIVE_KEYWORDS:
        if kw in desc_lower:
            return True
    return False

# ---------------------------------------------------------
# PROMPT 2: EXHIBITION CLASSIFICATION
# ---------------------------------------------------------
EXHIBITION_SYSTEM_INSTRUCTION = """
You are an AI screener for an IIT Bombay Mechanical Engineering placement office.
Your job is to classify companies exhibiting at hardware trade shows (like IMTEX, AutoExpo).

EXTRACT THRESHOLDS:
Use your internal world knowledge about the company to determine:
- company_age: 'Unknown' if you truly don't know, otherwise state the age (e.g., '5 yrs').
- company_type: Is it a Startup, MNC, or Listed? 
- global_presence: Is it operating in multiple countries? (Yes/No/Unknown).

Definitions:
- OEM: Companies that design and manufacture end-products. HIGH PRIORITY.
- Supplier: Companies that manufacture critical subsystems or parts for OEMs. HIGH PRIORITY.
- Engineering Services: Companies offering CAD/CAM/CAE or product design. MEDIUM PRIORITY.
- Tooling & Automation: Companies building custom manufacturing lines or industrial robots. HIGH PRIORITY.
- Irrelevant/Sales/Trading: Distributors, raw material traders, purely software platforms, or resellers. IGNORE.

Instructions:
1. Classify the company into exactly one of the defined categories.
2. Provide a 1-sentence justification detailing whether they do actual mechanical design/R&D in-house, or if they are just a trading/sales outfit.
3. Extract the key engineering capability.
4. Output as JSON. If Irrelevant, set is_relevant_for_mechanical_hiring to false.
"""

def analyze_exhibitor(company_name, description):
    if pre_filter_fails(description):
        return {"company_name": company_name, "classification": "Software/Irrelevant", "justification": "Pre-filtered", "key_technology": "N/A", "is_relevant_for_mechanical_hiring": False}
        
    if TEST_MODE:
        return {
            "company_name": company_name,
            "classification": "OEM",
            "justification": "Simulated hardware company.",
            "key_technology": "Robotics",
            "is_relevant_for_mechanical_hiring": "drop" not in company_name.lower(),
            "company_age": "Unknown",
            "company_type": "Unknown",
            "global_presence": "Unknown"
        }
        
    prompt = f"Company Name: {company_name}\nCompany Description: {description}\n"
    schema = {
        "type": types.Type.OBJECT,
        "properties": {
            "company_name": types.Schema(type=types.Type.STRING),
            "classification": types.Schema(type=types.Type.STRING, enum=["OEM", "Supplier", "Engineering Services", "Tooling & Automation", "Irrelevant/Sales/Trading"]),
            "justification": types.Schema(type=types.Type.STRING),
            "key_technology": types.Schema(type=types.Type.STRING),
            "is_relevant_for_mechanical_hiring": types.Schema(type=types.Type.BOOLEAN),
            "company_age": types.Schema(type=types.Type.STRING, description="Estimate age or return 'Unknown'"),
            "company_type": types.Schema(type=types.Type.STRING, description="MNC/Listed/Startup or 'Unknown'"),
            "global_presence": types.Schema(type=types.Type.STRING, description="Countries or 'Unknown'")
        },
        "required": ["company_name", "classification", "justification", "key_technology", "is_relevant_for_mechanical_hiring"]
    }
    
    return llm_waterfall(EXHIBITION_SYSTEM_INSTRUCTION, prompt, schema)

# ---------------------------------------------------------
# PROMPT 3: GOVERNMENT INITIATIVES (DSIR, iDEX, DPIIT)
# ---------------------------------------------------------
GOV_SYSTEM_INSTRUCTION = """
You are an expert industrial and deeptech analyst.
Your task is to analyze a short description of a company recognized by a government R&D portal (like DSIR, iDEX, or DPIIT) and classify them.

Definitions:
- Deeptech/Defense Hardware: Companies building defense tech, aerospace, rocketry, or advanced materials. HIGH PRIORITY.
- Industrial/Manufacturing: Companies designing/manufacturing CNCs, industrial automation, automotive parts, or physical products. HIGH PRIORITY.
- Irrelevant/Software: Fintech, Edtech, E-commerce, purely software platforms. IGNORE.

Instructions:
1. Classify the company into exactly one of the defined categories.
2. Provide a 1-sentence justification.
3. Extract the key technology being developed.
4. Output as JSON. If Irrelevant, set is_relevant_for_mechanical_hiring to false.
"""

def analyze_gov_initiative(company_name, description):
    if pre_filter_fails(description):
        return {"company_name": company_name, "classification": "Software/Irrelevant", "justification": "Pre-filtered", "key_technology": "N/A", "is_relevant_for_mechanical_hiring": False}

    if TEST_MODE:
        return {
            "company_name": company_name,
            "classification": "Industrial/Manufacturing",
            "justification": "Simulated hardware company.",
            "key_technology": "Robotics",
            "is_relevant_for_mechanical_hiring": "drop" not in company_name.lower(),
            "company_age": "Unknown",
            "company_type": "Unknown",
            "global_presence": "Unknown"
        }
        
    prompt = f"Company Name: {company_name}\nInitiative Description: {description}\n"
    schema = {
        "type": types.Type.OBJECT,
        "properties": {
            "company_name": types.Schema(type=types.Type.STRING),
            "classification": types.Schema(type=types.Type.STRING, enum=["Deeptech/Defense Hardware", "Industrial/Manufacturing", "Irrelevant/Software"]),
            "justification": types.Schema(type=types.Type.STRING),
            "key_technology": types.Schema(type=types.Type.STRING),
            "is_relevant_for_mechanical_hiring": types.Schema(type=types.Type.BOOLEAN),
            "company_age": types.Schema(type=types.Type.STRING, description="Estimate age or return 'Unknown'"),
            "company_type": types.Schema(type=types.Type.STRING, description="MNC/Listed/Startup or 'Unknown'"),
            "global_presence": types.Schema(type=types.Type.STRING, description="Countries or 'Unknown'")
        },
        "required": ["company_name", "classification", "justification", "key_technology", "is_relevant_for_mechanical_hiring"]
    }

    return llm_waterfall(GOV_SYSTEM_INSTRUCTION, prompt, schema)

# ---------------------------------------------------------
# PROMPT 4: PATENT ANALYSIS
# ---------------------------------------------------------
PATENT_SYSTEM_INSTRUCTION = """
You are an AI screener for an IIT Bombay Mechanical Engineering placement office.
Your job is to read startup funding news and classify the company.

EXTRACT THRESHOLDS:
Use your internal world knowledge about the company to determine:
- company_age: 'Unknown' if you truly don't know, otherwise state the age (e.g., '5 yrs').
- company_type: Is it a Startup, MNC, or Listed? 
- global_presence: Is it operating in multiple countries? (Yes/No/Unknown).

Definitions:
- Hardware/Mechanical: Patents involving physical structures, thermal management, robotics, automotive parts, fluid dynamics, or structural engineering. HIGH PRIORITY.
- Deeptech/Materials: Patents involving advanced materials, nanotechnology, or complex physical processes. HIGH PRIORITY.
- Software/IT: Patents involving blockchain, purely software methods, generic AI models, or data processing algorithms without hardware. IGNORE.

Instructions:
1. Classify the patent into exactly one of the defined categories.
2. Provide a 1-sentence justification.
3. Extract the key technology being patented.
4. Output as JSON. If Software/IT, set is_relevant_for_mechanical_hiring to false.
"""

def analyze_patent(company_name, description):
    if pre_filter_fails(description):
        return {"company_name": company_name, "classification": "Software/Irrelevant", "justification": "Pre-filtered", "key_technology": "N/A", "is_relevant_for_mechanical_hiring": False}

    if TEST_MODE:
        return {
            "company_name": company_name,
            "classification": "Hardware/Mechanical",
            "justification": "Simulated patent company.",
            "key_technology": "Robotics",
            "is_relevant_for_mechanical_hiring": True,
            "company_age": "Unknown",
            "company_type": "Unknown",
            "global_presence": "Unknown"
        }
        
    prompt = f"Company Name: {company_name}\nPatent Abstract: {description}\n"
    schema = {
        "type": types.Type.OBJECT,
        "properties": {
            "company_name": types.Schema(type=types.Type.STRING),
            "classification": types.Schema(type=types.Type.STRING, enum=["Hardware/Mechanical", "Deeptech/Materials", "Software/IT"]),
            "justification": types.Schema(type=types.Type.STRING),
            "key_technology": types.Schema(type=types.Type.STRING),
            "is_relevant_for_mechanical_hiring": types.Schema(type=types.Type.BOOLEAN),
            "company_age": types.Schema(type=types.Type.STRING, description="Estimate age or return 'Unknown'"),
            "company_type": types.Schema(type=types.Type.STRING, description="MNC/Listed/Startup or 'Unknown'"),
            "global_presence": types.Schema(type=types.Type.STRING, description="Countries or 'Unknown'")
        },
        "required": ["company_name", "classification", "justification", "key_technology", "is_relevant_for_mechanical_hiring"]
    }
    
    return llm_waterfall(PATENT_SYSTEM_INSTRUCTION, prompt, schema)
