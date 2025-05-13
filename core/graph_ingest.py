import os
import json
from datetime import datetime
from pathlib import Path
import asyncio
from core.graph_client import MSGraphClient
from core.auth import MSGraphAuth
import httpx
from core.openai_service import openai_service
import re
import base64
from pypdf import PdfReader
from docx import Document as DocxDocument
import pandas as pd
from core.vectorstore_upload import upload_to_vectorstore

ATTACHMENTS_DIR = Path("attachments")
ATTACHMENTS_DIR.mkdir(exist_ok=True)

EMAILS_JSONL = f"emails_{datetime.now().strftime('%Y%m%d')}.jsonl"

ONEDRIVE_ROOT = "PERS-MS-OPENAI"
ATTACHMENTS_ONEDRIVE_FOLDER = f"{ONEDRIVE_ROOT}/attachments"
JSONL_ONEDRIVE_FOLDER = f"{ONEDRIVE_ROOT}/jsonl"

# Set your vector store ID here (reuse this for all uploads)
VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID") or "vs_abc123..."  # TODO: Replace with your actual vector store ID

def sanitize_filename(name):
    name = re.sub(r'[\\/:"*?<>|]+', '_', name)
    name = name.replace(' ', '_')
    return name

# Fetch emails from Outlook using MS Graph
async def fetch_emails():
    user_email = os.environ.get("USER_EMAIL")
    if not user_email:
        raise ValueError("USER_EMAIL environment variable not set.")
    auth = MSGraphAuth(
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
        tenant_id=os.environ["TENANT_ID"]
    )
    client = MSGraphClient(auth=auth)
    # Fetch up to 50 emails for demo; adjust as needed
    emails = await client.get_outlook_emails(user_email=user_email, top=50)
    return emails

def download_attachment(email_id, attachment):
    # TODO: Replace with real download logic from MS Graph
    filename = f"{sanitize_filename(email_id)}_{sanitize_filename(attachment['name'])}"
    filepath = ATTACHMENTS_DIR / filename
    # Simulate download
    with open(filepath, "wb") as f:
        f.write(b"Attachment content")
    return str(filepath)

def remove_signature(text):
    # Remove common signature blocks
    return re.split(r'(--+|Best regards,|Sent from my|Kind regards,|Sincerely,|Cheers,|Thanks,|Thank you,)', text, flags=re.IGNORECASE)[0]

def remove_quoted(text):
    # Remove quoted/reply text (simple heuristic)
    return re.split(r'\nFrom: .*\nSent: .*\nTo: .*\nSubject: .*', text, flags=re.IGNORECASE)[0]

async def main():
    emails = await fetch_emails()
    user_email = os.environ.get("USER_EMAIL")
    with open(EMAILS_JSONL, "w", encoding="utf-8") as out:
        for email in emails:
            attachment_refs = []
            if getattr(email, "has_attachments", False):
                auth = MSGraphAuth(
                    client_id=os.environ["CLIENT_ID"],
                    client_secret=os.environ["CLIENT_SECRET"],
                    tenant_id=os.environ["TENANT_ID"]
                )
                client = MSGraphClient(auth=auth)
                attachments = await client.get_email_attachments(user_email, email.id)
                for att in attachments:
                    filename = f"{sanitize_filename(email.id)}_{sanitize_filename(att['name'])}"
                    filepath = ATTACHMENTS_DIR / filename
                    if att.get("contentBytes"):
                        with open(filepath, "wb") as f:
                            f.write(base64.b64decode(att["contentBytes"]))
                    elif att.get("@microsoft.graph.downloadUrl"):
                        # Download large file using downloadUrl
                        url = att["@microsoft.graph.downloadUrl"]
                        try:
                            async with httpx.AsyncClient() as http_client:
                                resp = await http_client.get(url)
                                resp.raise_for_status()
                                with open(filepath, "wb") as f:
                                    f.write(resp.content)
                        except Exception as e:
                            print(f"[WARN] Failed to download attachment {filename}: {e}")
                            continue
                    else:
                        # Try to fetch via $value endpoint
                        try:
                            endpoint = f"users/{user_email}/messages/{email.id}/attachments/{att['id']}/$value"
                            token = auth.get_graph_token()
                            url = f"https://graph.microsoft.com/v1.0/{endpoint}"
                            headers = {"Authorization": f"Bearer {token}"}
                            async with httpx.AsyncClient() as http_client:
                                resp = await http_client.get(url, headers=headers)
                                resp.raise_for_status()
                                with open(filepath, "wb") as f:
                                    f.write(resp.content)
                        except Exception as e:
                            print(f"[WARN] Could not fetch attachment {filename} via $value endpoint: {e}")
                            continue
                    password_protected = False
                    # Detect password-protected PDFs
                    if filename.lower().endswith('.pdf'):
                        try:
                            reader = PdfReader(str(filepath))
                            if reader.is_encrypted:
                                password_protected = True
                                print(f"[WARN] PDF attachment {filename} is password protected.")
                        except Exception as e:
                            print(f"[WARN] Could not check PDF {filename}: {e}")
                    # Detect password-protected DOCX
                    elif filename.lower().endswith('.docx'):
                        try:
                            DocxDocument(str(filepath))
                        except Exception as e:
                            if 'password' in str(e).lower():
                                password_protected = True
                                print(f"[WARN] DOCX attachment {filename} is password protected.")
                    # Detect password-protected XLSX
                    elif filename.lower().endswith(('.xlsx', '.xls')):
                        try:
                            pd.read_excel(str(filepath), nrows=1)
                        except Exception as e:
                            if 'password' in str(e).lower() or 'protected' in str(e).lower():
                                password_protected = True
                                print(f"[WARN] XLSX attachment {filename} is password protected.")
                    # Upload to OneDrive attachments folder
                    onedrive_id = None
                    onedrive_url = None
                    try:
                        upload_meta = await client.upload_file_to_onedrive(
                            str(filepath),
                            onedrive_folder="PERS-MS-OPENAI/attachments"
                        )
                        onedrive_id = upload_meta.get("id")
                        onedrive_url = upload_meta.get("webUrl")
                    except Exception as e:
                        print(f"[WARN] Failed to upload {filename} to OneDrive: {e}")
                        onedrive_id = None
                        onedrive_url = None
                    attachment_refs.append({
                        "name": att["name"],
                        "size": att.get("size"),
                        "content_type": att.get("contentType"),
                        "local_path": str(filepath),
                        "onedrive_id": onedrive_id,
                        "onedrive_url": onedrive_url,
                        "password_protected": password_protected
                    })
            # Clean HTML, remove signature and quoted text
            body_clean = openai_service.extract_text_from_html(email.body)
            body_clean = remove_signature(body_clean)
            body_clean = remove_quoted(body_clean)
            email_record = {
                "id": email.id,
                "subject": email.subject,
                "sender": email.sender,
                "recipients": email.recipients,
                "date": email.received_date.isoformat(),
                "body": body_clean,
                "attachments": attachment_refs,
                "has_attachments": getattr(email, "has_attachments", False),
                "importance": getattr(email, "importance", ""),
                "categories": getattr(email, "categories", []),
            }
            out.write(json.dumps(email_record) + "\n")
    print(f"[INFO] Wrote {len(emails)} emails to {EMAILS_JSONL}")
    # Upload the JSONL file to OneDrive
    try:
        auth = MSGraphAuth(
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
            tenant_id=os.environ["TENANT_ID"]
        )
        client = MSGraphClient(auth=auth)
        upload_meta = await client.upload_file_to_onedrive(sanitize_filename(EMAILS_JSONL), onedrive_folder=sanitize_filename(JSONL_ONEDRIVE_FOLDER))
        print(f"[INFO] Uploaded JSONL to OneDrive: {upload_meta.get('webUrl')}")
    except Exception as e:
        print(f"[WARN] Failed to upload JSONL to OneDrive: {e}")

    # Upload each email as a separate record to OpenAI Vector Store
    try:
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
                    "url": f"https://outlook.office.com/mail/id/{email_record['id']}"  # Placeholder, update if actual URL available
                }
                # Write email text to a temp file
                temp_path = f"tmp_email_{email_record['id']}.txt"
                with open(temp_path, "w", encoding="utf-8") as tempf:
                    tempf.write(email_text)
                try:
                    openai_file_id, _ = upload_to_vectorstore(
                        file_path=temp_path,
                        attributes=metadata,
                        vector_store_id=VECTOR_STORE_ID
                    )
                    print(f"[UPLOAD] Email {email_record['id']} → OpenAI file_id: {openai_file_id}")
                except Exception as e:
                    print(f"[WARN] Failed to upload email {email_record['id']} to OpenAI Vector Store: {e}")
                finally:
                    os.remove(temp_path)
    except Exception as e:
        print(f"[WARN] Failed to upload emails to OpenAI Vector Store: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 