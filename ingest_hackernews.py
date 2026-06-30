import urllib.request
import xml.etree.ElementTree as ET
from config import MAX_ARTICLES_PER_FEED
from ai_filter import analyze_funding_news

def scrape_hackernews():
    """Scrapes HackerNews RSS for Show HN and startups."""
    leads = []
    feed_url = "https://news.ycombinator.com/rss"
    print(f"[HackerNews] Fetching Y-Combinator Feed: {feed_url}")
    try:
        req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        # HN is noisy, we process top 20 items
        for item in items[:20]:
            title = item.find('title').text if item.find('title') is not None else "No Title"
            summary = item.find('description').text if item.find('description') is not None else "No Summary"
            
            print(f"[HackerNews] Analyzing: {title}")
            try:
                result = analyze_funding_news(title, summary)
                if result.get("is_relevant_for_mechanical_hiring"):
                    print(f"  ✅ MATCH: {result.get('company_name')} ({result.get('classification')})")
                    result["funnel_source"] = "Y-Combinator (HackerNews)"
                    leads.append(result)
                else:
                    print(f"  ❌ Ignored: {result.get('company_name', 'Unknown')}")
            except Exception as e:
                print(f"  [Error] analyzing article: {e}")
                
    except Exception as e:
         print(f"[Error] fetching HackerNews feed: {e}")
         
    return leads
