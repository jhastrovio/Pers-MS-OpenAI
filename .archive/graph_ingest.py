import os
import json
from datetime import datetime
from pathlib import Path
import asyncio
import re
import base64
from pypdf import PdfReader
from docx import Document as DocxDocument
import pandas as pd
from core.openai_service import openai_service

ATTACHMENTS_DIR = Path("attachments")
ATTACHMENTS_DIR.mkdir(exist_ok=True)

EMAILS_JSONL = f"emails_{datetime.now().strftime('%Y%m%d')}.jsonl"

# Set your vector store ID here (reuse this for all uploads)
VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID")

def sanitize_filename(name):
    name = re.sub(r'[\\/:"*?<>|]+', '_', name)
    name = name.replace(' ', '_')
    return name

def remove_signature(text):
    return re.split(r'(--+|Best regards,|Sent from my|Kind regards,|Sincerely,|Cheers,|Thanks,|Thank you,)', text, flags=re.IGNORECASE)[0]

def remove_quoted(text):
    return re.split(r'\nFrom: .*\nSent: .*\nTo: .*\nSubject: .*', text, flags=re.IGNORECASE)[0]

async def main():
    # Expect emails to be present in EMAILS_JSONL
    if not os.path.exists(EMAILS_JSONL):
        print(f"[ERROR] {EMAILS_JSONL} not found. Please provide a JSONL file with emails.")
        return
    with open(EMAILS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            email_record = json.loads(line)
            email_text = f"Subject: {email_record['subject']}\nFrom: {email_record['sender']}\nTo: {', '.join(email_record['recipients'])}\nDate: {email_record['date']}\n\n{email_record['body']}"
            metadata = {
                "id": email_record["id"],
                "name": email_record["subject"],
                "type": "email",
                "author": email_record["sender"],
                "recipients": email_record["recipients"],
                "date": email_record["date"],
                "has_attachments": email_record.get("has_attachments", False),
                "importance": email_record.get("importance", ""),
                "categories": email_record.get("categories", []),
                "url": f"https://outlook.office.com/mail/id/{email_record['id']}"  # Placeholder
            }
            temp_path = f"tmp_email_{email_record['id']}.txt"
            with open(temp_path, "w", encoding="utf-8") as tempf:
                tempf.write(email_text)
            try:
                openai_file_id = await openai_service.upload_file_to_file_search(
                    file_path=temp_path,
                    metadata=metadata
                )
                print(f"[UPLOAD] Email {email_record['id']} → OpenAI file_id: {openai_file_id}")
            except Exception as e:
                print(f"[WARN] Failed to upload email {email_record['id']} to OpenAI Vector Store: {e}")
            finally:
                os.remove(temp_path)

if __name__ == "__main__":
    asyncio.run(main()) 