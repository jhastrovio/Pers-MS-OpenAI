from typing import Dict, List, Optional, Tuple
import httpx
from pathlib import Path
import aiofiles
import asyncio
from .auth import MSGraphAuth
from .file_processor import FileProcessor
from .models import OutlookEmail
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MSGraphClient:
    def __init__(self, auth: MSGraphAuth, download_dir: str = "downloads"):
        self.auth = auth
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.file_processor = FileProcessor()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make an authenticated request to MS Graph API"""
        url = f"{self.base_url}/{endpoint}"
        token = self.auth.get_graph_token()
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "ConsistencyLevel": "eventual"  # Added for better query support
            }
            headers.update(kwargs.pop("headers", {}))
            
            logger.info(f"Making {method} request to: {url}")
            logger.info(f"With params: {kwargs.get('params', {})}")
            
            response = await client.request(method, url, headers=headers, **kwargs)
            try:
                response.raise_for_status()
                data = response.json()
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response data preview: {str(data)[:200]}...")
                return data
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                logger.error(f"Response content: {response.text}")
                raise

    async def fetch_drive_items(self, user_email: str, folder_path: str = "", download: bool = False, recursive: bool = True) -> List[Dict]:
        """Fetch OneDrive items with optional downloading and recursive folder traversal"""
        logger.info(f"Fetching items from folder: {folder_path if folder_path else 'root'}")
        
        endpoint = f"users/{user_email}/drive/root:/{folder_path}:/children"
        if not folder_path:
            endpoint = f"users/{user_email}/drive/root/children"
            
        params = {
            "$select": "id,name,size,file,folder,parentReference,webUrl,lastModifiedDateTime",
            "$orderby": "lastModifiedDateTime desc",
            "$top": "50"  # Get up to 50 items
        }
        
        try:
            logger.info(f"Making API request to endpoint: {endpoint}")
            async with httpx.AsyncClient(timeout=30.0) as client:  # 30 second timeout
                headers = {
                    "Authorization": f"Bearer {self.auth.get_graph_token()}",
                    "Accept": "application/json"
                }
                
                response = await client.get(
                    f"{self.base_url}/{endpoint}",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("value", [])
                logger.info(f"Found {len(items)} items in folder")
            
            # Add full path information
            for item in items:
                if "parentReference" in item:
                    parent_path = item["parentReference"].get("path", "").replace("/drive/root:", "")
                    item["full_path"] = f"{parent_path}/{item['name']}"
                else:
                    item["full_path"] = f"/{item['name']}"
            
            # If recursive, fetch items from subfolders
            if recursive:
                folders = [item for item in items if "folder" in item]
                logger.info(f"Found {len(folders)} subfolders to process")
                
                for folder in folders:
                    folder_path = folder["full_path"].lstrip("/")
                    logger.info(f"Processing subfolder: {folder_path}")
                    try:
                        subfolder_items = await self.fetch_drive_items(
                            user_email=user_email,
                            folder_path=folder_path,
                            download=download,
                            recursive=True
                        )
                        items.extend(subfolder_items)
                    except Exception as e:
                        logger.error(f"Error processing subfolder {folder_path}: {e}")
                        # Continue with other folders even if one fails
                        continue
            
            if download:
                logger.info("Starting file downloads and processing")
                await self._process_items(items)
            
            return items
            
        except Exception as e:
            logger.error(f"Error fetching OneDrive items from {folder_path}: {e}")
            raise

    async def _process_items(self, items: List[Dict]) -> None:
        """Process and download files if supported"""
        download_tasks = []
        
        for item in items:
            if "file" not in item:
                continue
                
            file_name = item.get("name")
            download_url = item.get("@microsoft.graph.downloadUrl")
            
            if not file_name or not download_url:
                continue
                
            file_path = self.download_dir / file_name
            
            if self.file_processor.can_process(file_name):
                download_tasks.append(self._download_and_process_file(download_url, file_path, item))
        
        if download_tasks:
            await asyncio.gather(*download_tasks)

    async def _download_and_process_file(self, download_url: str, file_path: Path, item: Dict) -> Tuple[bool, Optional[str]]:
        """Download and process a single file"""
        if await self._download_file(download_url, file_path):
            try:
                # Extract text content
                content = self.file_processor.extract_text(file_path)
                
                # Get metadata
                metadata = self.file_processor.get_metadata(file_path)
                
                # Update item with extracted data
                item["extracted_content"] = content
                item["local_metadata"] = metadata
                
                return True, content
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                return False, None
        
        return False, None

    async def _download_file(self, download_url: str, file_path: Path) -> bool:
        """Download a file from OneDrive"""
        token = self.auth.get_graph_token()
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {token}"}
                async with client.stream("GET", download_url, headers=headers) as response:
                    response.raise_for_status()
                    
                    async with aiofiles.open(file_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            await f.write(chunk)
                            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file {file_path}: {e}")
            return False

    async def get_outlook_emails(
        self,
        top: int = 10,
        skip: int = 0,
        filter: Optional[str] = None,
        max_pages: int = 1,
        user_email: Optional[str] = None
    ) -> List[OutlookEmail]:
        """Get emails from Outlook with enhanced error handling and pagination support"""
        if not user_email:
            raise ValueError("user_email is required for accessing messages")
            
        endpoint = f"users/{user_email}/messages"
        params = {
            "$top": top,
            "$skip": skip,
            "$select": "id,subject,body,from,toRecipients,receivedDateTime,hasAttachments,importance,categories",
            "$orderby": "receivedDateTime desc"
        }
        if filter:
            params["$filter"] = filter

        try:
            all_emails = []
            page_count = 0
            
            while page_count < max_pages:
                logger.info(f"Fetching page {page_count + 1} of emails for user {user_email}")
                data = await self._make_request("GET", endpoint, params=params)
                
                for item in data.get("value", []):
                    try:
                        email = OutlookEmail(
                            id=item["id"],
                            subject=item["subject"],
                            body=item["body"]["content"],
                            sender=item["from"]["emailAddress"]["address"],
                            recipients=[r["emailAddress"]["address"] for r in item["toRecipients"]],
                            received_date=datetime.fromisoformat(item["receivedDateTime"].replace("Z", "+00:00")),
                            has_attachments=item["hasAttachments"],
                            importance=item["importance"],
                            categories=item.get("categories")
                        )
                        all_emails.append(email)
                    except Exception as e:
                        logger.error(f"Error processing email {item.get('id', 'unknown')}: {str(e)}")
                        continue

                # Check for more pages
                next_link = data.get("@odata.nextLink", "")
                if not next_link or page_count + 1 >= max_pages:
                    break
                    
                # Extract skiptoken from next_link if present
                try:
                    if "$skiptoken=" in next_link:
                        skiptoken = next_link.split("$skiptoken=")[1].split("&")[0]
                        params = {
                            "$skiptoken": skiptoken,
                            "$select": params["$select"],
                            "$orderby": params["$orderby"]
                        }
                    else:
                        break
                except Exception as e:
                    logger.error(f"Error parsing next_link: {e}")
                    break
                
                page_count += 1
            
            logger.info(f"Successfully retrieved {len(all_emails)} emails from {page_count + 1} pages")
            return all_emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            raise

    async def get_file_url(self, file_id: str) -> str:
        """Get the web URL for a OneDrive file"""
        endpoint = f"me/drive/items/{file_id}"
        params = {"$select": "webUrl"}
        
        try:
            logger.info(f"Fetching web URL for file {file_id}")
            data = await self._make_request("GET", endpoint, params=params)
            return data.get("webUrl", "")
        except Exception as e:
            logger.error(f"Error getting file URL for {file_id}: {str(e)}")
            raise 