import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import sys
from google import genai
from google.genai import types

# Force UTF-8 encoding for Windows terminal printing
sys.stdout.reconfigure(encoding='utf-8')

# Setup Gemini Client (Requires GEMINI_API_KEY environment variable)
client = genai.Client()

FEEDS = [
    "http://inc42.com/category/startups/feed",
]

SYSTEM_INSTRUCTION = """
You are an expert venture capital analyst specializing in deeptech, manufacturing, and hardware startups.
Your task is to analyze a news article summary about a startup funding event and classify the startup.

Definitions:
- Hardware/Mechanical Startup: A company primarily building physical products (e.g., robotics, EVs, aerospace, IoT devices, battery tech, automation machinery, industrial equipment).
- Deeptech Startup: A company based on significant scientific breakthroughs or difficult-to-replicate physical IP (e.g., new materials, synthetic biology, space tech, quantum computing).
- Neither/Software: A company building SaaS, consumer apps, fintech, edtech, e-commerce, food delivery, or generic B2B software.

Instructions:
1. Determine if the startup qualifies as "Hardware", "Deeptech", "Both", or "Neither/Software".
2. Provide a 1-sentence justification based on the text.
3. Extract the startup's name.
4. Extract the primary product or technology mentioned.
5. If the startup is "Neither/Software", the company is irrelevant to us.
"""

def analyze_article(title, summary):
    prompt = f"Article Title: {title}\nArticle Summary: {summary}\n"
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "company_name": types.Schema(type=types.Type.STRING),
                    "classification": types.Schema(
                        type=types.Type.STRING, 
                        enum=["Hardware", "Deeptech", "Both", "Neither/Software"]
                    ),
                    "justification": types.Schema(
                        type=types.Type.STRING, 
                        description="A 1-sentence explanation of why it fits this classification."
                    ),
                    "key_technology": types.Schema(
                        type=types.Type.STRING, 
                        description="The core physical product or technology they are building."
                    ),
                    "is_relevant_for_mechanical_hiring": types.Schema(
                        type=types.Type.BOOLEAN, 
                        description="True if classification is Hardware, Deeptech, or Both"
                    )
                },
                required=["company_name", "classification", "justification", "key_technology", "is_relevant_for_mechanical_hiring"]
            ),
        ),
    )
    return json.loads(response.text)

def run_pipeline():
    print("Starting Funding Intelligence Pipeline...")
    
    for feed_url in FEEDS:
        print(f"\nFetching RSS Feed: {feed_url}")
        try:
            req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
            
            root = ET.fromstring(xml_data)
            # Find all <item> elements which contain the articles
            items = root.findall('.//item')
            
            for item in items[:10]:
                title = item.find('title').text if item.find('title') is not None else "No Title"
                summary = item.find('description').text if item.find('description') is not None else "No Summary"
                
                print(f"\nAnalyzing: {title}")
                try:
                    result = analyze_article(title, summary)
                    if result.get("is_relevant_for_mechanical_hiring"):
                        print("✅ MATCH FOUND!")
                        print(f"   Company: {result.get('company_name')}")
                        print(f"   Tech:    {result.get('key_technology')}")
                        print(f"   Why:     {result.get('justification')}")
                    else:
                        print(f"❌ Ignored (Software/Irrelevant): {result.get('company_name')}")
                except Exception as e:
                    print(f"   Error analyzing article: {e}")
        except Exception as e:
             print(f"Error fetching feed: {e}")

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: Please set the GEMINI_API_KEY environment variable.")
    else:
        run_pipeline()
