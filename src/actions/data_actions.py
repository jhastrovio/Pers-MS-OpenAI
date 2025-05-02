from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional
from ..core.models import DataEntry, SearchQuery, SearchResponse, DataSource
from ..core.data_access import DataAccess
from pydantic import BaseModel

router = APIRouter(prefix="/data", tags=["data"])

class QuestionRequest(BaseModel):
    question: str
    context_ids: List[str]

async def get_access_token(authorization: str = Header(...)) -> str:
    """Extract and validate the access token from the Authorization header"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization.split(" ")[1]

@router.get("/recent", response_model=List[DataEntry])
async def get_recent_data(
    limit: int = 10,
    access_token: str = Depends(get_access_token)
):
    """Get recent data entries from Outlook and OneDrive with AI-enhanced processing"""
    try:
        data_access = DataAccess(access_token)
        return await data_access.get_recent_data(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=SearchResponse)
async def search_data(
    query: SearchQuery,
    access_token: str = Depends(get_access_token)
):
    """Search data entries in Outlook and OneDrive with semantic search"""
    try:
        data_access = DataAccess(access_token)
        return await data_access.search_data(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer")
async def answer_question(
    request: QuestionRequest,
    access_token: str = Depends(get_access_token)
):
    """Answer a question about specific content"""
    try:
        data_access = DataAccess(access_token)
        answer = await data_access.answer_question(request.question, request.context_ids)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=DataEntry)
async def add_entry(
    content: str,
    metadata: Optional[dict] = None,
    access_token: str = Depends(get_access_token)
):
    """Add a new data entry"""
    try:
        data_access = DataAccess(access_token)
        return await data_access.add_entry(content, metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{entry_id}", response_model=DataEntry)
async def update_entry(
    entry_id: str,
    content: str,
    metadata: Optional[dict] = None,
    access_token: str = Depends(get_access_token)
):
    """Update an existing data entry"""
    try:
        data_access = DataAccess(access_token)
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
    access_token: str = Depends(get_access_token)
):
    """Delete a data entry"""
    try:
        data_access = DataAccess(access_token)
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