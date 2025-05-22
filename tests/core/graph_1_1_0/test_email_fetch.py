"""
Test script for email fetching functionality from Microsoft Graph API.
"""

import asyncio
import os
from core.graph_1_1_0.main import GraphClient
from core.utils.config import app_config, get_env_variable
from core.utils.logging import get_logger

logger = get_logger(__name__)

async def get_recent_emails(client: GraphClient, user_email: str, limit: int = 5) -> list:
    """Get recent emails from Outlook.
    
    Args:
        client: GraphClient instance
        user_email: User's email address
        limit: Maximum number of emails to fetch
        
    Returns:
        list: List of email metadata
    """
    try:
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get recent emails
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
        params = {
            "$top": limit,
            "$select": "id,subject,receivedDateTime,from,hasAttachments",
            "$orderby": "receivedDateTime desc"
        }
        
        response = await client.client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("value", [])
        
    except Exception as e:
        logger.error(f"Failed to get recent emails: {str(e)}")
        raise

async def main():
    """Main test function."""
    try:
        # Get user email from environment
        user_email = get_env_variable('user_email')
        if not user_email:
            raise ValueError("user_email environment variable not set")
            
        # Initialize client
        client = GraphClient()
        
        try:
            # Get recent emails
            logger.info(f"Fetching recent emails for {user_email}...")
            emails = await get_recent_emails(client, user_email, limit=10)
            
            if not emails:
                logger.info("No emails found")
                return
                
            # Print email summary
            logger.info(f"Found {len(emails)} recent emails:")
            for email in emails:
                logger.info(f"- {email['subject']} (ID: {email['id']})")
                logger.info(f"  From: {email['from']['emailAddress']['address']}")
                logger.info(f"  Received: {email['receivedDateTime']}")
                logger.info(f"  Has attachments: {email['hasAttachments']}")
                logger.info("---")
            
            # Process all emails
            processed_count = 0
            for email in emails:
                logger.info(f"\nProcessing email {processed_count + 1}: {email['subject']}")
                message_id = email['id']
                logger.info(f"Message ID: {message_id}")
                url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}"
                logger.info(f"Request URL: {url}")
                try:
                    result = await client.fetch_and_store_email(user_email, message_id)
                    # Print results
                    logger.info("Fetch and store results:")
                    logger.info(f"- EML path: {result['eml_path']}")
                    logger.info(f"- Number of attachments: {len(result['attachments'])}")
                    for att in result['attachments']:
                        logger.info(f"  - {att['name']} -> {att['path']}")
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error fetching email with ID {message_id}: {e}")
                    # Try the next email
                    continue
            
            logger.info(f"\nSuccessfully processed {processed_count} out of {len(emails)} emails")
                
        finally:
            await client.close()
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 