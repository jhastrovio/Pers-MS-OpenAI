from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum

class DataSource(Enum):
    OUTLOOK_EMAIL = "outlook_email"
    ONEDRIVE_FILE = "onedrive_file"
    MANUAL = "manual"

class DataEntry(BaseModel):
    id: str
    content: str
    source: DataSource
    source_id: str  # Email ID or File ID
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict] = None

class OutlookEmail(BaseModel):
    id: str
    subject: str
    body: str
    sender: str
    recipients: List[str]
    received_date: datetime
    has_attachments: bool
    importance: str
    categories: Optional[List[str]] = None

class OneDriveFile(BaseModel):
    id: str
    name: str
    path: str
    content: str
    last_modified: datetime
    size: int
    file_type: str
    created_by: str
    last_modified_by: str
    web_url: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    sources: Optional[List[DataSource]] = None
    filters: Optional[dict] = None
    limit: Optional[int] = 10
    offset: Optional[int] = 0

class SearchResponse(BaseModel):
    results: List[DataEntry]
    total_count: int
    page: int
    page_size: int 