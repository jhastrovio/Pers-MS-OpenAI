"""Integration tests for Microsoft Graph API.

These tests require valid Microsoft Graph API credentials and will make actual API calls.
They should be run separately from unit tests and may require specific environment setup.
"""
import os
import pytest
import asyncio
from core.graph_1_1_0.main import GraphClient
import dotenv
import re
from core.utils.config import config
import httpx
dotenv.load_dotenv()

print("CLIENT_ID:", os.getenv("CLIENT_ID"))
print("CLIENT_SECRET:", "set" if os.getenv("CLIENT_SECRET") else "not set")
print("TENANT_ID:", os.getenv("TENANT_ID"))
# ... existing code ...
# These tests are marked with a custom marker 'integration'
# They will be skipped unless explicitly run with: pytest -m integration

@pytest.mark.integration
async def test_real_graph_client_initialization():
    """Test GraphClient initialization with real credentials."""
    client = GraphClient()
    assert client.client_id is not None
    assert client.client_secret is not None
    assert client.tenant_id is not None

@pytest.mark.integration
async def test_real_email_retrieval():
    """Test actual email retrieval from Microsoft Graph."""
    client = GraphClient()
    emails = await client.get_emails()
    assert isinstance(emails, list)
    # Verify email structure
    if emails:
        assert 'id' in emails[0]
        assert 'subject' in emails[0]
        assert 'body' in emails[0]

@pytest.mark.integration
async def test_real_document_retrieval():
    """Test actual document retrieval from OneDrive."""
    client = GraphClient()
    documents = await client.get_documents()
    assert isinstance(documents, list)
    # Verify document structure
    if documents:
        assert 'id' in documents[0]
        assert 'name' in documents[0]
        assert 'size' in documents[0]

@pytest.mark.integration
async def test_real_attachment_retrieval():
    """Test actual attachment retrieval for an email."""
    client = GraphClient()
    # First get an email
    emails = await client.get_emails()
    if emails:
        message_id = emails[0]['id']
        attachments = await client.get_attachments(message_id)
        assert isinstance(attachments, list)
        # Verify attachment structure if any exist
        if attachments:
            assert 'id' in attachments[0]
            assert 'name' in attachments[0]
            assert 'contentType' in attachments[0]

@pytest.mark.integration
async def test_real_graph_email_fetch():
    # Only run if real credentials are present
    required_vars = ["client_id", "client_secret", "tenant_id"]
    if not all(os.getenv(k) for k in required_vars):
        pytest.skip("Real Graph credentials not set in environment variables")
    client = GraphClient()
    emails = await client.get_emails()
    assert isinstance(emails, list)

@pytest.mark.integration
async def test_save_email_to_onedrive():
    """Test saving an email to the specified OneDrive folder."""
    client = GraphClient()
    # Create a temporary email file for testing
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_file.write(b"Test email content")
        temp_file_path = temp_file.name

    try:
        # Save the email to OneDrive
        response = await client.save_to_onedrive(temp_file_path, "test_email.txt")
        assert response is not None
        # Optionally, verify the file exists in OneDrive
        # This would require an additional API call to check the file's existence
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

@pytest.mark.integration
async def test_pull_and_save_real_email_content():
    client = GraphClient()
    emails = await client.get_emails()
    assert emails, "No emails found to save!"

    # Take the first email and save its subject/body
    email = emails[0]
    subject = email.get("subject", "no_subject").replace("/", "_").replace("\\", "_")
    body = email.get("body", {}).get("content", "")

    file_name = f"email_{subject[:20].replace(' ', '_')}.txt"
    response = await client.save_email_content_to_onedrive(body, file_name)
    assert response is not None
    print("Saved email content to OneDrive:", response)

def sanitize_filename(name):
    name = re.sub(r'["*:<>?/\\|]', '', name)
    name = name.replace(' ', '_')
    return name[:100]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_first_10_emails_to_onedrive():
    client = GraphClient()
    emails = await client.get_emails()
    for i, email in enumerate(emails[:10]):
        subject = email.get("subject", "no_subject")
        safe_subject = sanitize_filename(subject)
        file_name = f"email_{safe_subject}_{i+1}.eml"
        folder = config["onedrive"]["emails_folder"]  # Use just 'emails_1' from config
        print(f"Uploading: {file_name} to folder: {folder}")
        headers = [
            f"Subject: {email.get('subject', '')}",
            f"From: {email.get('from', {}).get('emailAddress', {}).get('address', '')}",
            f"To: {', '.join([to.get('emailAddress', {}).get('address', '') for to in email.get('toRecipients', [])])}"
        ]
        body = email.get("body", {}).get("content", "No content")
        raw_email = "\n".join(headers) + "\n\n" + body
        try:
            result = await client.save_email_content_to_onedrive(raw_email, file_name, folder=folder)
            print(f"Saved: {file_name} to {folder}, Response: {result}")
            assert "id" in result
        except httpx.HTTPStatusError as e:
            print(f"Error uploading {file_name}: {e.response.text}")
            raise 