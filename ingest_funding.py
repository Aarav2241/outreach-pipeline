import urllib.request
import xml.etree.ElementTree as ET
import time
from feeds import RSS_FEEDS, MAX_ARTICLES_PER_FEED
from ai_filter import analyze_funding_news

FEED_NAMES = {
    "manufacturing.economictimes": "ET Manufacturing",
    "auto.economictimes/rss/auto-components": "ETAuto Components",
    "auto.economictimes/rss/auto-technology": "ETAuto Tech",
    "energy.economictimes": "ET Energy",
    "mtwmag.com": "Machine Tools World",
    "inc42.com": "Inc42",
    "yourstory.com": "YourStory",
    "entrackr.com": "Entrackr"
}

def get_feed_name(feed_url):
    for key, name in FEED_NAMES.items():
        if key in feed_url:
            return name
    return "Industry News"

def scrape_funding_feeds():
    """Scrapes RSS feeds, analyzes them with AI, and yields relevant leads one at a time."""
    
    for feed_url in RSS_FEEDS:
        feed_source_name = get_feed_name(feed_url)
        print(f"[{feed_source_name}] Fetching RSS Feed: {feed_url}")
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
                
                print(f"[{feed_source_name}] Analyzing: {title}")
                try:
                    result = analyze_funding_news(title, summary)
                    if result.get("is_relevant_for_mechanical_hiring"):
                        print(f"  ✅ MATCH: {result.get('company_name')} ({result.get('classification')})")
                        result["funnel_source"] = feed_source_name
                        result["source_link"] = link
                        yield result
                    else:
                         print(f"  ❌ Ignored: {result.get('company_name')}")
                except Exception as e:
                    print(f"  [Error] analyzing article: {e}")
        except Exception as e:
             print(f"[Error] fetching feed {feed_url}: {e}")
