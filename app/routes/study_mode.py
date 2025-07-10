import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user
from app.database.book_queries import get_book_structure_query
from app.database.connection import PostgresConnection
from app.database.study_mode_queries import (
    get_or_create_chat_session,
    get_last_position
)
from app.services.book_processor import get_doc_metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/study-mode", tags=["Study Mode"])

@router.get("/init")
async def study_mode_init(document_id: str, document_type: str, current_user: str = Depends(get_current_user)):
    try:
        with PostgresConnection() as conn:
            doc = get_doc_metadata(conn, document_id, document_type)

            if document_type != "book" and document_type != "presentation":
                raise HTTPException(status_code=400, detail="Study mode is only supported for books and slides right now.")

            chat_session = get_or_create_chat_session(conn, current_user, document_id, document_type)
            toc_structure = get_book_structure_query(conn, UUID(document_id))
            # last_position = get_last_position(conn, current_user, document_id, doc["type"])
            
            return {
                "document": doc,
                "chat_session_id": chat_session["id"],
                "toc": toc_structure,
                "last_position": {
                    "page_number": 0,
                    "section_id": None, 
                    "chapter_id": None,
                }
            }

    except Exception as e:
        logger.error(f"[Study Mode Init] Failed to init study mode: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Study mode init failed")
