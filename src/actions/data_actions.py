import os
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ..core.models import DataEntry, SearchQuery, SearchResponse, DataSource
from ..core.data_access import DataAccess
from ..core.auth import MSGraphAuth
from pydantic import BaseModel

router = APIRouter(prefix="/data", tags=["data"])

class QuestionRequest(BaseModel):
    question: str
    context_ids: List[str]

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

@router.post("/search", response_model=SearchResponse)
async def search_data(
    query: SearchQuery,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Search data entries in Outlook and OneDrive with semantic search"""
    try:
        data_access = DataAccess(auth)
        return await data_access.search_data(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer")
async def answer_question(
    request: QuestionRequest,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Answer a question about specific content"""
    try:
        data_access = DataAccess(auth)
        answer = await data_access.answer_question(request.question, request.context_ids)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=DataEntry)
async def add_entry(
    content: str,
    metadata: Optional[dict] = None,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Add a new data entry"""
    try:
        data_access = DataAccess(auth)
        return await data_access.add_entry(content, metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{entry_id}", response_model=DataEntry)
async def update_entry(
    entry_id: str,
    content: str,
    metadata: Optional[dict] = None,
    auth: MSGraphAuth = Depends(get_auth)
):
    """Update an existing data entry"""
    try:
        data_access = DataAccess(auth)
        entry = await data_access.update_entry(entry_id, content, metadata)
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