from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union
import json

@dataclass
class EmailDocumentMetadata:
    document_id: str
    type: str  # 'email' or 'document'
    filename: str
    one_drive_url: str
    created_at: str
    size: int
    content_type: str
    source: str
    is_attachment: bool = False
    parent_email_id: Optional[str] = None
    parent_document_id: Optional[str] = None
    message_id: Optional[str] = None
    subject: Optional[str] = None
    from_: Optional[str] = None  # 'from' is a reserved word
    to: Optional[List[str]] = field(default_factory=list)
    cc: Optional[List[str]] = field(default_factory=list)
    date: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    last_modified: Optional[str] = None
    attachments: Optional[List[str]] = field(default_factory=list)  # list of document_ids
    tags: Optional[List[str]] = field(default_factory=list)
    text_content: Optional[str] = None  # OCR or extracted text

    def to_dict(self) -> dict:
        d = asdict(self)
        # Rename 'from_' to 'from' for JSON output
        d['from'] = d.pop('from_')
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> 'EmailDocumentMetadata':
        # Accept both 'from' and 'from_' in input
        if 'from' in d:
            d['from_'] = d.pop('from')
        return cls(**d)

    @classmethod
    def from_json(cls, s: str) -> 'EmailDocumentMetadata':
        return cls.from_dict(json.loads(s)) 