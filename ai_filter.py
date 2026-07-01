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
# PROMPT 1: INDUSTRY & FUNDING NEWS CLASSIFICATION
# ---------------------------------------------------------
FUNDING_SYSTEM_INSTRUCTION = """
You are an expert industrial analyst and placement officer for IIT Bombay Mechanical Engineering.
Your task is to analyze a news article summary and classify whether the company mentioned is relevant for hiring mechanical, automotive, manufacturing, or hardware engineers in India.

Definitions:
- Mechanical/Manufacturing/Auto OEM: Companies manufacturing physical vehicles, auto components, heavy machinery, defense equipment, industrial robotics, or energy equipment. HIGH PRIORITY.
- Deeptech/Hardware Startup: Indian startups building physical products, EVs, drones, aerospace tech, battery systems, or IoT hardware. HIGH PRIORITY.
- Neither/Software/Irrelevant: SaaS platforms, fintech, edtech, consumer apps, e-commerce, D2C fashion, HR tech, IT services, or non-engineering companies. IGNORE.

Instructions:
1. Determine if the company qualifies as "Mechanical/Manufacturing", "Deeptech/Hardware", "Both", or "Neither/Software".
2. Provide a 1-sentence justification detailing why mechanical/hardware engineers would or would not be needed there.
3. Extract the company's name accurately.
4. Extract the primary engineering product or technology mentioned.
5. If the company is "Neither/Software" or not relevant to physical hardware/manufacturing, set is_relevant_for_mechanical_hiring to false.
"""

def analyze_funding_news(title, summary):
    if TEST_MODE:
        return {
            "company_name": "Test Company",
            "classification": "Mechanical/Manufacturing",
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
            "classification": types.Schema(type=types.Type.STRING, enum=["Mechanical/Manufacturing", "Deeptech/Hardware", "Both", "Neither/Software"]),
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
    "crypto", "nft", "fintech", "adtech", "talent platform",
    "edtech", "social media", "influencer", "d2c", "direct to consumer",
    "food delivery", "quick commerce", "gaming", "esports",
    "hr tech", "hrtech", "martech", "legaltech", "proptech",
    "fantasy sports", "dating app", "content creator",
    "digital marketing", "seo agency", "web development"
]

def pre_filter_fails(description):
    """Returns True if the description contains instant-drop negative keywords."""
    desc_lower = description.lower()
    for kw in NEGATIVE_KEYWORDS:
        if kw in desc_lower:
            return True
    return False
