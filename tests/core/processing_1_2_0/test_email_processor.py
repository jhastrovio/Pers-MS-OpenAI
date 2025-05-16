"""
Tests for the EmailProcessor class.
"""

import asyncio
import os
import pytest
import json
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.utils.config import config
from httpx import HTTPStatusError

@pytest.fixture
def email_processor():
    """Create an EmailProcessor instance for testing."""
    return EmailProcessor(config["processing"])

@pytest.mark.asyncio
async def test_email_processing_workflow():
    """Test the complete email processing workflow for up to 10 emails:
    1. Read raw emails from OneDrive
    2. Process each email
    3. Verify each is saved to the processed folder as JSON
    4. Verify metadata and content
    """
    processor = EmailProcessor(config["processing"])
    client = GraphClient()
    
    try:
        # Get source and target folders from config
        source_folder = config["onedrive"]["emails_folder"]
        target_folder = config["onedrive"]["processed_emails_folder"]
        user_email = os.getenv("USER_EMAIL")
        
        if not user_email:
            pytest.skip("USER_EMAIL environment variable not set")
        
        # Get access token
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            # List files in source folder
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{source_folder}:/children"
            response = await client.client.get(url, headers=headers)
            response.raise_for_status()
            items = response.json().get("value", [])
            eml_files = [item["name"] for item in items if item["name"].lower().endswith(".eml")]
            
            if not eml_files:
                pytest.skip("No EML files found for testing")
            
            # Process up to 10 EML files
            for file_name in eml_files[:10]:
                file_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{source_folder}/{file_name}:/content"
                response = await client.client.get(file_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                eml_bytes = response.content
                # Process the email using the public process method
                result = await processor.process(eml_bytes, filename=file_name)
                
                # Verify the result
                assert result['filename'].endswith('.json')
                assert result['metadata'].subject
                assert result['metadata'].from_
                assert result['metadata'].to
                assert result['metadata'].one_drive_url  # Verify OneDrive URL was set
                
                # Verify the JSON file was uploaded to the correct folder
                verify_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{target_folder}/{result['filename']}"
                verify_response = await client.client.get(verify_url, headers=headers)
                verify_response.raise_for_status()
                
                # Verify the JSON content
                content_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{target_folder}/{result['filename']}:/content"
                content_response = await client.client.get(content_url, headers=headers, follow_redirects=True)
                content_response.raise_for_status()
                
                # Parse and verify JSON content
                json_content = json.loads(content_response.content)
                assert json_content['subject'] == result['subject']
                assert json_content['metadata']['text_content'] == result['metadata'].text_content
                assert json_content['metadata']['subject'] == result['metadata'].subject
                assert json_content['metadata']['from_'] == result['metadata'].from_
                assert json_content['metadata']['to'] == result['metadata'].to
                
                # Verify attachments if any
                for attachment in result.get('attachments', []):
                    assert attachment['metadata'].one_drive_url  # Verify attachment URL was set
                    # Verify attachment was uploaded
                    att_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{target_folder}/{attachment['filename']}"
                    att_response = await client.client.get(att_url, headers=headers)
                    att_response.raise_for_status()
            
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                pytest.skip("OneDrive folder not found. Please create the folder first.")
            raise
            
    except Exception as e:
        pytest.fail(f"Integration test failed: {str(e)}")

@pytest.mark.asyncio
async def test_email_with_attachment():
    """Test processing an email with an attachment:
    1. Create a sample EML with an attachment
    2. Process the email
    3. Verify the attachment is processed and uploaded
    """
    processor = EmailProcessor(config["processing"])
    client = GraphClient()
    
    try:
        # Create a sample EML with an attachment
        sample_eml = (
            b'From: sender@example.com\r\n'
            b'To: recipient@example.com\r\n'
            b'Subject: Test Email with Attachment\r\n'
            b'Date: Thu, 16 May 2025 12:00:00 +0000\r\n'
            b'Message-ID: <test123@example.com>\r\n'
            b'MIME-Version: 1.0\r\n'
            b'Content-Type: multipart/mixed; boundary="boundary123"\r\n'
            b'\r\n'
            b'--boundary123\r\n'
            b'Content-Type: text/plain\r\n'
            b'\r\n'
            b'This is a test email with an attachment.\r\n'
            b'\r\n'
            b'--boundary123\r\n'
            b'Content-Type: application/octet-stream\r\n'
            b'Content-Disposition: attachment; filename="test.txt"\r\n'
            b'\r\n'
            b'This is a test attachment.\r\n'
            b'\r\n'
            b'--boundary123--\r\n'
        )
        
        # Process the email
        result = await processor.process(sample_eml, filename="test_email_with_attachment.eml")
        
        # Verify the result
        assert result['filename'].endswith('.json')
        assert result['metadata'].subject == "Test Email with Attachment"
        assert result['metadata'].from_ == "sender@example.com"
        assert result['metadata'].to == ["recipient@example.com"]
        assert result['metadata'].one_drive_url  # Verify OneDrive URL was set
        
        # Verify the attachment
        assert len(result.get('attachments', [])) == 1
        attachment = result['attachments'][0]
        assert attachment['filename'] == "test.txt"
        assert attachment['metadata'].one_drive_url  # Verify attachment URL was set
        
        # Verify the attachment was uploaded
        user_email = os.getenv("USER_EMAIL")
        if not user_email:
            pytest.skip("USER_EMAIL environment variable not set")
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        att_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{config['onedrive']['processed_emails_folder']}/{attachment['filename']}"
        att_response = await client.client.get(att_url, headers=headers)
        att_response.raise_for_status()
        
    except Exception as e:
        pytest.fail(f"Attachment test failed: {str(e)}")

if __name__ == "__main__":
    pytest.main([__file__]) 