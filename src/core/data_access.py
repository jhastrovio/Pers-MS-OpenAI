from typing import List, Optional, Dict
from datetime import datetime
import uuid
import os
from .models import DataEntry, SearchQuery, SearchResponse, DataSource, OutlookEmail, OneDriveFile
from .graph_client import MSGraphClient
from .auth import MSGraphAuth
from .openai_service import openai_service

class DataAccess:
    def __init__(self, auth: MSGraphAuth):
        self.client = MSGraphClient(auth=auth)  # Use enhanced client
        # Cache for storing processed data
        self._cache = {}

    async def get_recent_data(self, limit: int = 10) -> List[DataEntry]:
        """Get recent data from both Outlook and OneDrive with AI-enhanced processing"""
        entries = []
        user_email = os.environ["USER_EMAIL"]
        
        # Get recent emails
        emails = await self.client.get_outlook_emails(top=limit, user_email=user_email)
        for email in emails:
            # Get AI-enhanced information
            summary = await openai_service.summarize_text(email.body)
            key_info = await openai_service.extract_key_info(email.body)
            sentiment = await openai_service.analyze_sentiment(email.body)
            
            entry = DataEntry(
                id=str(uuid.uuid4()),
                content=f"Subject: {email.subject}\n\n{email.body}",
                source=DataSource.OUTLOOK_EMAIL,
                source_id=email.id,
                created_at=email.received_date,
                updated_at=email.received_date,
                metadata={
                    "sender": email.sender,
                    "recipients": email.recipients,
                    "has_attachments": email.has_attachments,
                    "importance": email.importance,
                    "categories": email.categories,
                    "summary": summary,
                    "key_info": key_info,
                    "sentiment": sentiment,
                    "url": f"https://outlook.office.com/mail/id/{email.id}"  # Add Outlook URL
                }
            )
            entries.append(entry)

        # Get recent files
        files = await self.client.get_onedrive_files(user_email=user_email, top=limit)
        for file in files:
            content = await self.client.get_file_content(file.id)
            # Get AI-enhanced information
            summary = await openai_service.summarize_text(content)
            key_info = await openai_service.extract_key_info(content)
            
            entry = DataEntry(
                id=str(uuid.uuid4()),
                content=content,
                source=DataSource.ONEDRIVE_FILE,
                source_id=file.id,
                created_at=file.last_modified,
                updated_at=file.last_modified,
                metadata={
                    "name": file.name,
                    "path": file.path,
                    "size": file.size,
                    "file_type": file.file_type,
                    "created_by": file.created_by,
                    "last_modified_by": file.last_modified_by,
                    "summary": summary,
                    "key_info": key_info,
                    "url": file.web_url  # Add OneDrive URL
                }
            )
            entries.append(entry)

        # Sort by creation date and limit results
        entries.sort(key=lambda x: x.created_at, reverse=True)
        return entries[:limit]

    async def search_data(self, query: SearchQuery) -> SearchResponse:
        """Search across Outlook and OneDrive with semantic search"""
        results = []
        
        # Get embeddings for the search query
        query_embedding = (await openai_service.get_embeddings([query.query]))[0]
        
        # Search in specified sources or all if none specified
        sources = query.sources or [DataSource.OUTLOOK_EMAIL, DataSource.ONEDRIVE_FILE]
        user_email = os.environ["USER_EMAIL"]

        if DataSource.OUTLOOK_EMAIL in sources:
            # Search in emails
            emails = await self.client.get_outlook_emails(
                top=query.limit,
                skip=query.offset,
                user_email=user_email
            )
            for email in emails:
                # Get embeddings for email content
                content_embedding = (await openai_service.get_embeddings([email.body]))[0]
                # Calculate similarity (simple cosine similarity)
                similarity = sum(a * b for a, b in zip(query_embedding, content_embedding))
                
                if similarity > 0.7:  # Threshold for semantic similarity
                    summary = await openai_service.summarize_text(email.body)
                    key_info = await openai_service.extract_key_info(email.body)
                    
                    entry = DataEntry(
                        id=str(uuid.uuid4()),
                        content=f"Subject: {email.subject}\n\n{email.body}",
                        source=DataSource.OUTLOOK_EMAIL,
                        source_id=email.id,
                        created_at=email.received_date,
                        updated_at=email.received_date,
                        metadata={
                            "sender": email.sender,
                            "recipients": email.recipients,
                            "has_attachments": email.has_attachments,
                            "importance": email.importance,
                            "categories": email.categories,
                            "summary": summary,
                            "key_info": key_info,
                            "similarity_score": similarity,
                            "url": f"https://outlook.office.com/mail/id/{email.id}"  # Add Outlook URL
                        }
                    )
                    results.append(entry)

        if DataSource.ONEDRIVE_FILE in sources:
            # Search in files
            files = await self.client.get_onedrive_files(
                user_email=user_email,
                top=query.limit,
                skip=query.offset
            )
            for file in files:
                content = await self.client.get_file_content(file.id)
                # Get embeddings for file content
                content_embedding = (await openai_service.get_embeddings([content]))[0]
                # Calculate similarity
                similarity = sum(a * b for a, b in zip(query_embedding, content_embedding))
                
                if similarity > 0.7:  # Threshold for semantic similarity
                    summary = await openai_service.summarize_text(content)
                    key_info = await openai_service.extract_key_info(content)
                    
                    entry = DataEntry(
                        id=str(uuid.uuid4()),
                        content=content,
                        source=DataSource.ONEDRIVE_FILE,
                        source_id=file.id,
                        created_at=file.last_modified,
                        updated_at=file.last_modified,
                        metadata={
                            "name": file.name,
                            "path": file.path,
                            "size": file.size,
                            "file_type": file.file_type,
                            "created_by": file.created_by,
                            "last_modified_by": file.last_modified_by,
                            "summary": summary,
                            "key_info": key_info,
                            "similarity_score": similarity,
                            "url": file.web_url  # Add OneDrive URL
                        }
                    )
                    results.append(entry)

        # Apply filters if provided
        if query.filters:
            filtered_results = []
            for entry in results:
                if all(entry.metadata.get(k) == v for k, v in query.filters.items()):
                    filtered_results.append(entry)
            results = filtered_results

        # Sort by similarity score
        results.sort(key=lambda x: x.metadata.get("similarity_score", 0), reverse=True)

        # Apply pagination
        start = query.offset
        end = start + query.limit
        paginated_results = results[start:end]

        return SearchResponse(
            results=paginated_results,
            total_count=len(results),
            page=query.offset // query.limit + 1,
            page_size=query.limit
        )

    async def add_entry(self, content: str, metadata: Optional[dict] = None) -> DataEntry:
        """Add a new data entry"""
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow()
        entry = DataEntry(
            id=entry_id,
            content=content,
            created_at=now,
            updated_at=now,
            metadata=metadata
        )
        self._cache[entry_id] = entry
        return entry

    async def update_entry(self, entry_id: str, content: str, metadata: Optional[dict] = None) -> Optional[DataEntry]:
        """Update an existing data entry"""
        if entry_id not in self._cache:
            return None
        
        entry = self._cache[entry_id]
        entry.content = content
        entry.updated_at = datetime.utcnow()
        if metadata is not None:
            entry.metadata = metadata
        return entry

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete a data entry"""
        if entry_id in self._cache:
            del self._cache[entry_id]
            return True
        return False

    async def answer_question(self, question: str, context_ids: List[str]) -> str:
        """Answer a question about specific content"""
        context_parts = []
        urls = []  # Store URLs for reference
        
        for context_id in context_ids:
            # Try to find the content in cache
            if context_id in self._cache:
                entry = self._cache[context_id]
                context_parts.append(entry.content)
                if entry.metadata and "url" in entry.metadata:
                    urls.append(entry.metadata["url"])
            else:
                # If not in cache, try to fetch from source
                # This is a simplified version - you might want to implement proper source lookup
                pass
        
        context = "\n\n".join(context_parts)
        answer = await openai_service.answer_question(context, question)
        
        # Add URLs to the answer if available
        if urls:
            answer += "\n\nRelevant documents:\n" + "\n".join(f"- {url}" for url in urls)
        
        return answer 