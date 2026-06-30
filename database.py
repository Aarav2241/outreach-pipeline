import sqlite3
from datetime import datetime
from config import DB_PATH

def init_db():
    """Initializes the SQLite database and creates/alters the leads table."""
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
    
    for col in ["linkedin_url", "email_pattern", "company_age", "company_type", "global_presence"]:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()

def insert_lead(company_name, funnel_source, classification, key_technology, justification, contact_emails, linkedin_url, email_pattern=None, company_age="Unknown", company_type="Unknown", global_presence="Unknown"):
    """Inserts a new lead into the database. Returns True if inserted, False if it already exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = False
    
    try:
        cursor.execute('''
        INSERT INTO leads (company_name, funnel_source, classification, key_technology, justification, date_added, contact_emails, linkedin_url, email_pattern, company_age, company_type, global_presence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (company_name, funnel_source, classification, key_technology, justification, datetime.now().isoformat(), contact_emails, linkedin_url, email_pattern, company_age, company_type, global_presence))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        # Company already exists in DB (UNIQUE constraint failed)
        inserted = False
    finally:
        conn.close()
        
    return inserted

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
