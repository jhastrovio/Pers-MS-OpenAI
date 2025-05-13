import os
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from core.models import DataEntry, SearchQuery, SearchResponse, DataSource, Message, APIResponse
from core.data_access import DataAccess
from core.auth import MSGraphAuth
from pydantic import BaseModel

router = APIRouter(prefix="/data", tags=["data"])

class QuestionRequest(BaseModel):
    question: str
    context_ids: List[str]

class AddEntryRequest(BaseModel):
    content: str
    metadata: Optional[dict] = None

class UpdateEntryRequest(BaseModel):
    content: str
    metadata: Optional[dict] = None

def get_auth():
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    tenant_id = os.environ["TENANT_ID"]
    return MSGraphAuth(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id
    )

@router.get("/recent", response_model=List[DataEntry])
async def get_recent_data(
    limit: int = 10,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Get recent data entries from Outlook and OneDrive with AI-enhanced processing"""
    try:
        data_access = DataAccess(auth)
        return await data_access.get_recent_data(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=APIResponse)
async def search_data(
    query: SearchQuery,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Search data entries in Outlook and OneDrive with semantic search"""
    try:
        data_access = DataAccess(auth)
        search_response = await data_access.search_data(query)
        count = len(search_response.results)
        if count == 0:
            message = "No results found for your search. Please try a different query."
            code = "NO_RESULTS"
        else:
            message = f"Found {count} results matching your search."
            code = "SUCCESS"
        return APIResponse(
            messages=[Message(role="assistant", content=message)],
            data=search_response,
            code=code
        )
    except Exception as e:
        return APIResponse(
            messages=[Message(role="assistant", content=f"An error occurred: {str(e)}")],
            data=None,
            code="ERROR"
        )

@router.post("/answer", response_model=APIResponse)
async def answer_question(
    request: QuestionRequest,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Answer a question about specific content"""
    try:
        data_access = DataAccess(auth)
        answer = await data_access.answer_question(request.question, request.context_ids)
        message = "Here is the answer to your question."
        return APIResponse(
            messages=[Message(role="assistant", content=message)],
            data={"answer": answer},
            code="SUCCESS"
        )
    except Exception as e:
        return APIResponse(
            messages=[Message(role="assistant", content=f"An error occurred: {str(e)}")],
            data=None,
            code="ERROR"
        )

@router.post("/", response_model=DataEntry)
async def add_entry(
    request: AddEntryRequest,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Add a new data entry"""
    try:
        data_access = DataAccess(auth)
        return await data_access.add_entry(request.content, request.metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{entry_id}", response_model=DataEntry)
async def update_entry(
    entry_id: str,
    request: UpdateEntryRequest,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Update an existing data entry"""
    try:
        data_access = DataAccess(auth)
        entry = await data_access.update_entry(entry_id, request.content, request.metadata)
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Delete a data entry"""
    try:
        data_access = DataAccess(auth)
        success = await data_access.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Entry not found")
        return {"message": "Entry deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources", response_model=List[str])
async def get_available_sources():
    """Get available data sources"""
    return [source.value for source in DataSource] 