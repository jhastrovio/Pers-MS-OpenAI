import asyncio
import json
from pathlib import Path
from datetime import datetime
from core.auth import MSGraphAuth
from core.graph_client import MSGraphClient
import os

# Remove secrets.json loading, use environment variables instead
config = {
    "client_id": os.environ["CLIENT_ID"],
    "client_secret": os.environ["CLIENT_SECRET"],
    "tenant_id": os.environ["TENANT_ID"],
    "user_email": os.environ["USER_EMAIL"]
}

async def load_config():
    """Load configuration from config/secrets.json"""
    try:
        config_path = Path("config/secrets.json")
        if not config_path.exists():
            raise FileNotFoundError("secrets.json not found. Please create it in the config directory.")
            
        config = json.loads(config_path.read_text())
        required_fields = ["client_id", "client_secret", "tenant_id", "user_email"]
        
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {', '.join(missing_fields)}")
            
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        raise

async def test_email_fetch(client: MSGraphClient, user_email: str):
    """Test email fetching"""
    print("\n=== Testing Email Fetch ===")
    try:
        emails = await client.fetch_emails(user_email, max_pages=2)
        print(f"Successfully fetched {len(emails)} emails")
        
        # Display sample of emails
        for i, email in enumerate(emails[:5], 1):
            print(f"\nEmail {i}:")
            print(f"Subject: {email.get('subject', 'No subject')}")
            print(f"From: {email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')}")
            print(f"Received: {email.get('receivedDateTime', 'Unknown')}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error testing email fetch: {e}")

async def test_document_fetch(client: MSGraphClient, user_email: str):
    """Test document fetching and processing"""
    print("\n=== Testing Document Fetch ===")
    try:
        # Try fetching from root first
        items = await client.fetch_drive_items(
            user_email=user_email,
            download=True  # Enable automatic download and processing
        )
        
        print(f"Successfully fetched {len(items)} items from root")
        
        # Display sample of processed documents
        processed_items = [item for item in items if "file" in item]
        for i, item in enumerate(processed_items[:5], 1):
            print(f"\nDocument {i}:")
            print(f"Name: {item.get('name', 'Unknown')}")
            print(f"Type: {item.get('file', {}).get('mimeType', 'Unknown')}")
            print(f"Size: {item.get('size', 0)} bytes")
            
            if "extracted_content" in item:
                content_preview = item["extracted_content"][:200] if item["extracted_content"] else "No content extracted"
                print(f"Content Preview: {content_preview}...")
            
            print("-" * 50)
            
    except Exception as e:
        print(f"Error testing document fetch: {e}")

async def main():
    try:
        # Load configuration
        config = await load_config()
        
        # Initialize components
        auth = MSGraphAuth(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            tenant_id=config["tenant_id"]
        )
        
        client = MSGraphClient(
            auth=auth,
            download_dir="test_downloads"
        )
        
        # Run tests
        await test_email_fetch(client, config["user_email"])
        await test_document_fetch(client, config["user_email"])
        
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 