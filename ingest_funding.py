import urllib.request
import xml.etree.ElementTree as ET
import time
from feeds import RSS_FEEDS, MAX_ARTICLES_PER_FEED
from ai_filter import analyze_funding_news, pre_filter_fails
from pipeline_status import status_feed, status_article, status_match, status_error
from database import is_url_processed, mark_url_processed

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

_articles_scanned = 0
_matches_found = 0
_articles_skipped = 0

def get_feed_name(feed_url):
    for key, name in FEED_NAMES.items():
        if key in feed_url:
            return name
    return "Industry News"

def scrape_funding_feeds():
    """Scrapes RSS feeds, analyzes them with AI, and yields relevant leads one at a time.
    
    Deduplication flow (saves LLM tokens):
      1. Check if the article URL has already been processed → skip entirely
      2. Check negative keywords (SaaS, fintech, etc.) → skip without LLM call
      3. Call LLM to classify → only for genuinely new, potentially relevant articles
    """
    global _articles_scanned, _matches_found, _articles_skipped
    _articles_scanned = 0
    _matches_found = 0
    _articles_skipped = 0
    
    for feed_url in RSS_FEEDS:
        feed_source_name = get_feed_name(feed_url)
        print(f"[{feed_source_name}] Fetching RSS Feed: {feed_url}")
        status_feed(feed_source_name)
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
                
                # ── DEDUP GATE 1: Skip articles we've already analyzed ──
                if is_url_processed(link):
                    _articles_skipped += 1
                    print(f"  ⏭️ Already seen: {title[:60]}")
                    continue
                
                # ── DEDUP GATE 2: Negative keyword pre-filter (no LLM cost) ──
                combined_text = f"{title} {summary}"
                if pre_filter_fails(combined_text):
                    mark_url_processed(link)  # remember we've seen it
                    _articles_skipped += 1
                    print(f"  🚫 Keyword reject: {title[:60]}")
                    continue
                
                # ── GATE 3: LLM classification (only for new, potentially relevant articles) ──
                _articles_scanned += 1
                print(f"[{feed_source_name}] Analyzing: {title}")
                status_article(feed_source_name, title, _articles_scanned)
                
                try:
                    result = analyze_funding_news(title, summary)
                    mark_url_processed(link)  # remember we've analyzed it regardless of result
                    
                    if result and result.get("is_relevant_for_mechanical_hiring"):
                        _matches_found += 1
                        print(f"  ✅ MATCH: {result.get('company_name')} ({result.get('classification')})")
                        status_match(result.get('company_name', 'Unknown'), _matches_found)
                        result["funnel_source"] = feed_source_name
                        result["source_link"] = link
                        yield result
                    else:
                        company = result.get('company_name', 'Unknown') if result else 'Parse Error'
                        print(f"  ❌ Ignored: {company}")
                except Exception as e:
                    mark_url_processed(link)  # don't retry broken articles
                    print(f"  [Error] analyzing article: {e}")
                    status_error(str(e))
        except Exception as e:
             print(f"[Error] fetching feed {feed_url}: {e}")
             status_error(f"Feed error ({feed_source_name}): {e}")
    
    print(f"\n[Ingestion Summary] Analyzed: {_articles_scanned} | Skipped (already seen/keyword): {_articles_skipped} | Matches: {_matches_found}")
