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
    """Metadata for emails and documents retrieved from Graph API.
    
    Fields:
        document_id: Unique identifier for the document
        type: Type of document ('email' or 'extension')
        filename: Name of the file in storage
        source_url: URL to the source (OneDrive URL or Outlook URL)
        is_attachment: Whether this is an email attachment
        parent_email_id: ID of parent email if this is an attachment
        message_id: Email message ID
        subject: Email subject or document title
        from_: Sender email address
        recipients: List of recipient email addresses
        date: Date of email or document creation
        title: Document title (if not an email)
        author: Document author (if not an email)
        attachments: List of attachments if parent email
        tags: List of tags/categories
        text_content: Extracted text content
    """
    
    document_id: str
    type: str  # 'email' or 'extension'
    filename: Optional[str] = None
    source_url: Optional[str] = None
    is_attachment: bool = False
    parent_email_id: Optional[str] = None
    message_id: Optional[str] = None
    subject: Optional[str] = None
    from_: Optional[str] = None  # Using underscore to avoid conflict with Python keyword
    recipients: List[str] = field(default_factory=list)
    date: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    text_content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format.
        
        Returns:
            Dict containing all metadata fields with proper naming.
        """
        d = asdict(self)
        # Rename 'from_' to 'from' for JSON output
        if 'from_' in d:
            d['from'] = d.pop('from_')
        # Ensure source_url is never null
        if d.get('source_url') is None:
            d['source_url'] = ""
        return d

    def to_json(self) -> str:
        """Convert metadata to JSON string.
        
        Returns:
            JSON string representation of metadata.
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    @classmethod
    def from_dict(cls, d: dict) -> 'EmailDocumentMetadata':
        """Create metadata instance from dictionary.
        
        Args:
            d: Dictionary containing metadata fields
            
        Returns:
            New EmailDocumentMetadata instance
        """
        # Accept both 'from' and 'from_' in input
        if 'from' in d:
            d['from_'] = d.pop('from')
        return cls(**d)

    @classmethod
    def from_json(cls, s: str) -> 'EmailDocumentMetadata':
        """Create metadata instance from JSON string.
        
        Args:
            s: JSON string containing metadata
            
        Returns:
            New EmailDocumentMetadata instance
        """
        return cls.from_dict(json.loads(s))

