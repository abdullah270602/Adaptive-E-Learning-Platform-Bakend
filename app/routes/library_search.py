from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional
from app.auth.dependencies import get_current_user
from app.services.rag_service import perform_library_search
from app.schemas.library_search import LibrarySearchRequest, LibrarySearchResponse
from app.database.library_queries import get_user_document_counts
from app.services.vector_search import get_collection_stats
from app.database.connection import PostgresConnection
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["Library Search"])

@router.post("/search", response_model=LibrarySearchResponse, status_code=status.HTTP_200_OK)
async def search_library(
    request: LibrarySearchRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Search across user's document library using RAG
    """
    try:
        # Validate query
        if not request.query or len(request.query.strip()) < 3:
            raise HTTPException(
                status_code=400, 
                detail="Query must be at least 3 characters long"
            )
        
        logger.info(f"Library search request from user {current_user}: '{request.query}'")
        
        # Perform RAG search with optimal defaults for document diversity
        result = await perform_library_search(
            query=request.query.strip(),
            user_id=current_user,
            max_chunks=20,  # More chunks for better document coverage
            document_types=None,  # Search all document types
            min_score=0.25  # Even lower threshold for maximum recall
        )
        
        logger.info(f"Library search completed for user {current_user}: {len(result.get('references', []))} sources found")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Library search failed for user {current_user}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Search failed. Please try again."
        )


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_library_stats(current_user: str = Depends(get_current_user)):
    """
    Get user's library statistics for search
    """
    try:
        with PostgresConnection() as conn:
            doc_counts = get_user_document_counts(conn, current_user)
            vector_stats = get_collection_stats(current_user)
            
            return {
                "documents": doc_counts,
                "vector_collection": vector_stats,
                "search_available": vector_stats.get("exists", False) and doc_counts.get("total", 0) > 0
            }
            
    except Exception as e:
        logger.error(f"Failed to get library stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get library statistics")


@router.get("/health", status_code=status.HTTP_200_OK)
async def library_search_health():
    """Health check for library search functionality"""
    try:
        from app.services.vector_search import client
        
        # Test vector DB connection
        collections = client.get_collections()
        
        return {
            "status": "healthy",
            "vector_db": "connected",
            "collections_count": len(collections.collections) if collections else 0
        }
        
    except Exception as e:
        logger.error(f"Library search health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
