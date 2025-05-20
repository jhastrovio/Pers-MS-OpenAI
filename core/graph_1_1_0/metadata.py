"""
Metadata classes for Graph API operations.

This module contains classes for handling metadata of documents and emails
retrieved from Microsoft Graph API.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union, Dict, Any
import json
from datetime import datetime, timedelta

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that converts datetime objects to ISO format strings."""
    def default(self, obj):
        if isinstance(obj, (datetime, timedelta)):
            return obj.isoformat()
        return super().default(obj)

@dataclass
class EmailDocumentMetadata:
    """Metadata for emails and documents retrieved from Graph API."""
    
    document_id: str
    type: str  # 'email' or 'document'
    filename: str = None
    one_drive_url: str = None
    outlook_url: str = None
    created_at: str = None
    size: int = None
    content_type: str = None
    source: str = None
    is_attachment: bool = False
    parent_email_id: str = None
    message_id: str = None
    subject: str = None
    from_: str = None  # Using underscore to avoid conflict with Python keyword
    to: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    date: str = None
    title: str = None
    author: str = None
    last_modified: str = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    text_content: str = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format."""
        d = asdict(self)
        # Rename 'from_' to 'from' for JSON output
        if 'from_' in d:
            d['from'] = d.pop('from_')
        # Make sure one_drive_url is never null in the output
        if d.get('one_drive_url') is None:
            d['one_drive_url'] = ""
        return d

    def to_json(self) -> str:
        """Convert metadata to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    @classmethod
    def from_dict(cls, d: dict) -> 'EmailDocumentMetadata':
        """Create metadata instance from dictionary."""
        # Accept both 'from' and 'from_' in input
        if 'from' in d:
            d['from_'] = d.pop('from')
        return cls(**d)

    @classmethod
    def from_json(cls, s: str) -> 'EmailDocumentMetadata':
        """Create metadata instance from JSON string."""
        return cls.from_dict(json.loads(s)) 