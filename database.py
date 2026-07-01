import sqlite3
from datetime import datetime
from config import DB_PATH

def init_db():
    """Initializes the SQLite database and creates/alters the tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the central leads table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT UNIQUE NOT NULL,
        funnel_source TEXT NOT NULL,
        classification TEXT,
        key_technology TEXT,
        justification TEXT,
        date_added TEXT,
        contact_emails TEXT,
        contact_status TEXT DEFAULT 'Pending'
    )
    ''')
    
    # Table: Deduplication Guard (Prevents re-scraping same URLs)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS processed_urls (
        url TEXT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Table: Company Firmographic Profiles (Enrichment Cache)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS company_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        domain TEXT,
        employee_count TEXT,
        revenue_range TEXT,
        sector TEXT,
        founded_year TEXT,
        funding_raised TEXT,
        enrichment_source TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    for col in ["linkedin_url", "email_pattern", "company_age", "company_type", "global_presence", "enrichment_source", "source_link"]:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()

def insert_lead(company_name, funnel_source, classification, key_technology, justification, contact_emails, linkedin_url, email_pattern=None, company_age="Unknown", company_type="Unknown", global_presence="Unknown", enrichment_source="OSINT API", source_link="N/A"):
    """Inserts a new lead into the database. Returns True if inserted, False if it already exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = False
    
    try:
        cursor.execute('''
        INSERT INTO leads (company_name, funnel_source, classification, key_technology, justification, date_added, contact_emails, linkedin_url, email_pattern, company_age, company_type, global_presence, enrichment_source, source_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (company_name, funnel_source, classification, key_technology, justification, datetime.now().isoformat(), contact_emails, linkedin_url, email_pattern, company_age, company_type, global_presence, enrichment_source, source_link))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        # Company already exists in DB (UNIQUE constraint failed)
        inserted = False
    finally:
        conn.close()
        
    return inserted

def is_url_processed(url):
    """Checks if a URL has already been processed by the scraper."""
    if not url:
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_urls WHERE url = ?", (url.strip(),))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def mark_url_processed(url):
    """Marks a URL as processed."""
    if not url:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO processed_urls (url) VALUES (?)", (url.strip(),))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def get_cached_profile(company_name):
    """Retrieves a cached company profile from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM company_profiles WHERE lower(name) = lower(?)", (company_name.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_cached_profile(name, domain, employee_count="Unknown", revenue_range="Unknown", sector="Mechanical / DeepTech", founded_year="Unknown", funding_raised="Unknown", enrichment_source="Cache"):
    """Saves or updates a company profile in SQLite cache."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO company_profiles (name, domain, employee_count, revenue_range, sector, founded_year, funding_raised, enrichment_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            domain=excluded.domain,
            employee_count=excluded.employee_count,
            revenue_range=excluded.revenue_range,
            sector=excluded.sector,
            founded_year=excluded.founded_year,
            funding_raised=excluded.funding_raised,
            enrichment_source=excluded.enrichment_source,
            timestamp=CURRENT_TIMESTAMP
        ''', (name.strip(), domain, employee_count, revenue_range, sector, founded_year, funding_raised, enrichment_source))
        conn.commit()
    except Exception as e:
        print(f"[Database] Cache save error: {e}")
    finally:
        conn.close()

def count_extracted_leads_today():
    """Counts how many leads with verified (Extracted) emails were added today."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads WHERE date(date_added) = date('now', 'localtime') AND contact_emails LIKE '%(Extracted)%'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_leads():
    """Retrieves all leads from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads ORDER BY date_added DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
