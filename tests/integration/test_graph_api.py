"""Integration tests for Microsoft Graph API functionality"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
import pytest
from src.core.auth import MSGraphAuth
from src.core.graph_client import MSGraphClient
import logging

logger = logging.getLogger(__name__)

@pytest.fixture
async def graph_client():
    """Fixture to create a Graph client for testing"""
    config = await load_config()
    auth = MSGraphAuth(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        tenant_id=config["tenant_id"]
    )
    return MSGraphClient(
        auth=auth,
        download_dir="test_downloads"
    )

@pytest.fixture
async def test_config():
    """Fixture to load test configuration"""
    return await load_config()

async def load_config():
    """Load configuration from config/secrets.json"""
    try:
        config_path = Path("config/secrets.json")
        if not config_path.exists():
            raise FileNotFoundError(
                "secrets.json not found. Please copy secrets.json.template "
                "to secrets.json and fill in your credentials."
            )
            
        config = json.loads(config_path.read_text())
        required_fields = ["client_id", "client_secret", "tenant_id", "user_email"]
        
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {', '.join(missing_fields)}")
            
        return config
    except Exception as e:
        pytest.skip(f"Failed to load config: {e}")

@pytest.mark.asyncio
async def test_permissions(graph_client, test_config):
    """Test Graph API permissions"""
    client = await graph_client
    config = await test_config
    
    print("\n=== Testing API Permissions ===")
    
    # Test application permissions
    try:
        response = await client._make_request("GET", "organization")
        print("\n✅ Organization access OK")
    except Exception as e:
        print(f"\n❌ Organization access failed: {e}")
    
    # Test user access
    try:
        response = await client._make_request("GET", "users")
        print("\n✅ Users access OK")
        print(f"Found {len(response.get('value', []))} users")
    except Exception as e:
        print(f"\n❌ Users access failed: {e}")
    
    # Test mail access
    try:
        response = await client._make_request(
            "GET", 
            f"users/{config['user_email']}/messages",
            params={"$top": "1", "$select": "subject"}
        )
        print("\n✅ Mail access OK")
        print(f"Can see messages: {'value' in response}")
    except Exception as e:
        print(f"\n❌ Mail access failed: {e}")
        print("\nMake sure the application has Mail.Read permission")
    
    # Test mailbox settings
    try:
        response = await client._make_request("GET", f"users/{config['user_email']}/mailboxSettings")
        print("\n✅ Mailbox settings access OK")
    except Exception as e:
        print(f"\n❌ Mailbox settings access failed: {e}")
        print("\nMake sure the application has MailboxSettings.Read permission")

@pytest.mark.asyncio
async def test_email_fetch(graph_client, test_config):
    """Test email fetching functionality"""
    client = await graph_client
    config = await test_config
    
    print("\n=== Testing Email Access ===")
    
    # Create output directory if it doesn't exist
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "email_test_results.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== Email Test Results ===\n\n")
        
        # Fetch emails with more details
        try:
            response = await client._make_request(
                "GET",
                f"users/{config['user_email']}/messages",
                params={
                    "$top": "10",
                    "$select": "subject,receivedDateTime,from,bodyPreview,body,importance,hasAttachments",
                    "$orderby": "receivedDateTime desc"
                }
            )
            
            if isinstance(response, dict) and 'value' in response:
                messages = response['value']
                output = f"\nFound {len(messages)} recent emails:\n"
                output += "\n" + "="*100 + "\n"
                
                for idx, msg in enumerate(messages, 1):
                    output += f"\nEmail {idx}:\n"
                    output += f"Subject: {msg.get('subject', 'No subject')}\n"
                    output += f"From: {msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')}\n"
                    output += f"Received: {msg.get('receivedDateTime', 'Unknown')}\n"
                    output += f"Importance: {msg.get('importance', 'normal')}\n"
                    output += f"Has Attachments: {msg.get('hasAttachments', False)}\n"
                    output += "\nPreview:\n"
                    output += "-" * 80 + "\n"
                    output += f"{msg.get('bodyPreview', 'No preview available')}\n"
                    output += "-" * 80 + "\n"
                    
                    # Show full body content if available
                    if 'body' in msg and msg['body'].get('content'):
                        output += "\nFull Content (first 500 chars):\n"
                        output += "=" * 80 + "\n"
                        content = msg['body']['content']
                        output += f"{content[:500] + '...' if len(content) > 500 else content}\n"
                        output += "=" * 80 + "\n"
                    
                    output += "\n" + "-"*100 + "\n"
                
                print(output)  # Still show in console
                f.write(output)  # Save to file
            else:
                output = "\nNo emails found in direct query\n"
                print(output)
                f.write(output)
                
        except Exception as e:
            error_msg = f"\nError accessing emails: {e}\n"
            print(error_msg)
            f.write(error_msg)
            raise

        # Test the fetch_emails method
        try:
            output = "\n=== Testing Email Fetch Method ===\n"
            emails = await client.get_outlook_emails(
                top=10,
                max_pages=1,
                user_email=config["user_email"]
            )
            output += f"\nget_outlook_emails retrieved {len(emails)} emails\n"
            
            if emails:
                output += "\nMost recent emails:\n"
                output += "="*100 + "\n"
                
                for idx, email in enumerate(emails[:5], 1):
                    output += f"\nEmail {idx}:\n"
                    output += f"Subject: {email.subject}\n"
                    output += f"From: {email.sender}\n"
                    output += f"Received: {email.received_date}\n"
                    output += f"Has Attachments: {email.has_attachments}\n"
                    output += f"Importance: {email.importance}\n"
                    output += "\nPreview:\n"
                    output += "-" * 80 + "\n"
                    preview = email.body[:200] + "..." if len(email.body) > 200 else email.body
                    output += f"{preview}\n"
                    output += "-" * 80 + "\n"
                    output += "\n" + "-"*100 + "\n"
                
                if len(emails) > 5:
                    output += f"\n... and {len(emails) - 5} more emails\n"
            else:
                output += "\nNo emails returned from get_outlook_emails method\n"
            
            print(output)  # Show in console
            f.write(output)  # Save to file
                
        except Exception as e:
            error_msg = f"\nError in get_outlook_emails: {e}\n"
            print(error_msg)
            f.write(error_msg)
            raise
    
    print(f"\nTest results have been saved to: {output_file}")

@pytest.mark.asyncio
async def test_document_fetch(graph_client, test_config):
    """Test document fetching and processing"""
    client = await graph_client
    config = await test_config
    
    print("\n=== Testing OneDrive Document Access ===")
    
    # Create output directory if it doesn't exist
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "onedrive_test_results.txt"
    
    # Specify the folder you want to examine
    target_folder = "FXStrategy"  # You can change this to any folder name
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"=== OneDrive Test Results for folder: {target_folder} ===\n\n")
        
        try:
            print(f"\nFetching items from {target_folder} (without downloading)...")
            # First try without downloading to see the structure
            items = await client.fetch_drive_items(
                user_email=config["user_email"],
                folder_path=target_folder,
                download=False,  # Don't download files yet
                recursive=False  # Don't traverse subfolders yet
            )
            
            if items:
                output = f"\nFound {len(items)} items in {target_folder}:\n"
                output += "\n" + "="*100 + "\n"
                
                # First list folders
                folders = [item for item in items if "folder" in item]
                if folders:
                    output += "\n=== Subfolders ===\n"
                    for idx, folder in enumerate(folders, 1):
                        output += f"\nFolder {idx}:\n"
                        output += f"Name: {folder.get('name', 'Unnamed')}\n"
                        output += f"Path: {folder.get('parentReference', {}).get('path', 'Unknown')}/{folder.get('name', '')}\n"
                        output += f"Items in folder: {folder.get('folder', {}).get('childCount', 0)}\n"
                        output += f"Last Modified: {folder.get('lastModifiedDateTime', 'Unknown')}\n"
                        output += "-"*80 + "\n"
                
                # Then list files
                files = [item for item in items if "file" in item]
                if files:
                    output += "\n=== Files ===\n"
                    for idx, file in enumerate(files, 1):
                        output += f"\nFile {idx}:\n"
                        output += f"Name: {file.get('name', 'Unnamed')}\n"
                        output += f"Type: {file['file'].get('mimeType', 'Unknown')}\n"
                        output += f"Size: {file.get('size', 0):,} bytes\n"
                        output += f"Path: {file.get('parentReference', {}).get('path', 'Unknown')}/{file.get('name', '')}\n"
                        output += f"Last Modified: {file.get('lastModifiedDateTime', 'Unknown')}\n"
                        output += f"Web URL: {file.get('webUrl', 'No URL available')}\n"
                        output += "\n" + "-"*100 + "\n"
                
                print(output)  # Show in console
                f.write(output)  # Save to file
                
                # Ask if we should proceed with downloading
                print("\nWould you like to download and process the files? (This will be implemented in the next step)")
                
            else:
                output = f"\nNo items found in folder: {target_folder}\n"
                print(output)
                f.write(output)
                
        except Exception as e:
            error_msg = f"\nError accessing OneDrive folder {target_folder}: {e}\n"
            print(error_msg)
            f.write(error_msg)
            raise
    
    print(f"\nTest results have been saved to: {output_file}")
    
    # Keep the original assertions for test validity
    assert items is not None 