from pydantic import BaseModel, Field
from typing import Optional, List

class CompanyProfile(BaseModel):
    name: str
    domain: Optional[str] = None
    employee_count: Optional[str] = "Unknown"
    revenue_range: Optional[str] = "Unknown"
    sector: Optional[str] = "Mechanical / DeepTech"
    founded_year: Optional[str] = "Unknown"
    funding_raised: Optional[str] = "Unknown"
    enrichment_source: Optional[str] = "Cache"

class EnrichedLead(BaseModel):
    company_name: str
    funnel_source: str
    classification: str
    key_technology: str
    justification: str
    contact_emails: str
    linkedin_url: str
    email_pattern: Optional[str] = None
    company_age: Optional[str] = "Unknown"
    company_type: Optional[str] = "Unknown"
    global_presence: Optional[str] = "Unknown"
    enrichment_source: Optional[str] = "OSINT API"
