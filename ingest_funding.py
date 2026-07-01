import urllib.request
import xml.etree.ElementTree as ET
import time
from config import RSS_FEEDS, MAX_ARTICLES_PER_FEED
from ai_filter import analyze_funding_news

def scrape_funding_feeds():
    """Scrapes RSS feeds, analyzes them with AI, and yields relevant leads."""
    leads = []
    
    for feed_url in RSS_FEEDS:
        print(f"[Funding] Fetching RSS Feed: {feed_url}")
        try:
            req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
            
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            
            for item in items[:MAX_ARTICLES_PER_FEED]:
                title = item.find('title').text if item.find('title') is not None else "No Title"
                summary = item.find('description').text if item.find('description') is not None else "No Summary"
                link = item.find('link').text if item.find('link') is not None and item.find('link').text else feed_url
                
                print(f"[Funding] Analyzing: {title}")
                try:
                    result = analyze_funding_news(title, summary)
                    if result.get("is_relevant_for_mechanical_hiring"):
                        print(f"  ✅ MATCH: {result.get('company_name')} ({result.get('classification')})")
                        result["funnel_source"] = "Funding News"
                        result["source_link"] = link
                        leads.append(result)
                    else:
                         print(f"  ❌ Ignored: {result.get('company_name')}")
                except Exception as e:
                    print(f"  [Error] analyzing article: {e}")
        except Exception as e:
             print(f"[Error] fetching feed {feed_url}: {e}")
             
    return leads
