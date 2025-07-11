import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from app.auth.dependencies import get_current_user
from app.database.book_queries import get_book_structure_query
from app.database.connection import PostgresConnection
from app.database.study_mode_queries import (
    get_or_create_chat_session,
    get_last_position
)
from app.services.book_processor import get_doc_metadata
from app.services.minio_client import MinIOClientContext, get_file_from_minio

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


@router.get("/documents/{document_id}/stream")
def stream_document(document_id: str, document_type: str, current_user: str = Depends(get_current_user)):
    try:
        with PostgresConnection() as conn:
            metadata = get_doc_metadata(conn, document_id, document_type)

        if not metadata or not metadata.get("s3_key"):
            raise HTTPException(status_code=404, detail="Document not found or missing S3 key")

        s3_key = metadata["s3_key"]
        with MinIOClientContext() as s3:
            file_stream = get_file_from_minio(s3, s3_key)

        return StreamingResponse(file_stream, media_type="application/pdf")

    except Exception as e:
        import traceback; traceback.print_exc();
        raise HTTPException(status_code=500, detail=f"Error streaming document: {str(e)}")