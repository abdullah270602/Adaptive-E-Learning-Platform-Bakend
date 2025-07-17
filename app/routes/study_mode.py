from datetime import datetime
import json
import logging
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.auth.dependencies import get_current_user
from app.cache.metadata import get_cached_doc_metadata
from app.database.book_queries import get_book_structure_query
from app.database.connection import PostgresConnection
from app.database.study_mode_queries import (
    get_chat_history,
    get_or_create_chat_session,
    get_last_position,
    get_tool_response_by_id,
    update_document_progress
)
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse
from app.schemas.document_progress import DocumentProgressUpdate
from app.services.constants import ASSISTANT_ROLE
from app.services.minio_client import MinIOClientContext, get_file_from_minio
from app.services.study_mode import handle_chat_message, save_interaction_to_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/study-mode", tags=["Study Mode"])

@router.get("/init", status_code=status.HTTP_200_OK)
async def study_mode_init(document_id: str, document_type: str, current_user: str = Depends(get_current_user)):
    """ Initialize study mode for a specific document """
    try:
        with PostgresConnection() as conn:
            doc = get_cached_doc_metadata(conn, str(document_id), document_type)
            doc.pop("s3_key", None)  # Remove S3 key from the response
            
            if document_type != "book" and document_type != "presentation":
                raise HTTPException(status_code=400, detail="Study mode is only supported for books and slides right now.")

            chat_session = get_or_create_chat_session(conn, current_user, document_id, document_type)
            toc_structure = get_book_structure_query(conn, UUID(document_id))
            last_position = get_last_position(conn, current_user, document_id, document_type)
            
            return {
                "document": doc,
                "chat_session_id": chat_session["id"],
                "toc": toc_structure,
                "last_position": last_position or {}
            }

    except Exception as e:
        logger.error(f"[Study Mode Init] Failed to init study mode: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Study mode init failed")


@router.get("/documents/{document_id}/stream")
def stream_document(document_id: str, document_type: str, current_user: str = Depends(get_current_user)):
    """ Stream the document content from S3 bucket """
    try:
        with PostgresConnection() as conn:
            metadata = get_cached_doc_metadata(conn, document_id, document_type)

        if not metadata or not metadata.get("s3_key"):
            raise HTTPException(status_code=404, detail="Document not found or missing S3 key")

        s3_key = metadata["s3_key"]
        with MinIOClientContext() as s3:
            file_stream = get_file_from_minio(s3, s3_key)

        return StreamingResponse(file_stream, media_type="application/pdf")

    except Exception as e:
        import traceback; traceback.print_exc();
        raise HTTPException(status_code=500, detail=f"Error streaming document: {str(e)}")


@router.post("/documents/{document_id}/last-position", status_code=status.HTTP_200_OK)
def update_last_position(
    request: DocumentProgressUpdate,
    user_id: str = Depends(get_current_user),
):
    """ Update the last read position for a document """
    document_id = request.document_id
    document_type = request.document_type
    page_number = request.page_number
    section_id = request.section_id
    chapter_id = request.chapter_id

    if not document_type:
        raise HTTPException(status_code=400, detail="document_type is required.")

    with PostgresConnection() as conn:
        update_document_progress(
            conn=conn,
            user_id=user_id,
            document_id=document_id,
            document_type=document_type,
            page_number=page_number,
            section_id=section_id,
            chapter_id=chapter_id,
        )

    return {"message": "Last position saved."}


@router.post("/chat/message", status_code=status.HTTP_201_CREATED, response_model=ChatMessageResponse)
async def create_chat_message(
    request: ChatMessageCreate,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """ Handle a chat message from the user and get a reply from the model """
    try:
        llm_reply = await handle_chat_message(request, current_user)
        tool_response_id = None
        if llm_reply.get("tool_name"):
            tool_response_id = uuid4()

        # Save both messages and tool response in the background
        background_tasks.add_task(
            save_interaction_to_db,
            chat_session_id=request.chat_session_id,
            user_msg=request.content,
            llm_msg=llm_reply.get("llm_reply", None),
            model_id=str(request.model_id),
            tool_name=llm_reply.get("tool_name", None),
            tool_response_id=tool_response_id,
            tool_response=llm_reply.get("tool_response", None),
        )
        
        response = ChatMessageResponse(
            chat_session_id=str(request.chat_session_id),
            user_id=current_user,
            role= ASSISTANT_ROLE,
            content=llm_reply.get("llm_reply", "PLACEHOLDER"),
            model_id=str(request.model_id),
            tool_type=llm_reply.get("tool_name", None),
            tool_response_id=tool_response_id,
            tool_response=llm_reply.get("tool_response", None),
            created_at=datetime.utcnow(),
        )

        return response

    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"[Create Chat Message] Failed to create chat message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat Message creation failed, Please try again.")


@router.get("/chat/{chat_session_id}/history")
async def get_chat_history_endpoint(
    chat_session_id: UUID,
    current_user: str = Depends(get_current_user),
):
    """
    Get full chat history for a given session ID, optionally limit the number of messages.
    """
    try:
        with PostgresConnection() as conn:
            messages = get_chat_history(conn, chat_session_id)
        return {"chat_session_id": chat_session_id, "messages": messages}
    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"[Get Chat History] Failed to retrieve chat history: {str(e)}")
        return {"error": "Failed to retrieve chat history."}
    
    
@router.get("tool-response/{tool_response_id}")
async def get_tool_response(
    tool_response_id: UUID,
    current_user: str = Depends(get_current_user),
):
    """
    Get the tool response by its ID.
    """
    try:
        with PostgresConnection() as conn:
            response = get_tool_response_by_id(conn, tool_response_id)
            response["response_text"] = None
            return response
        if not response:
            raise HTTPException(status_code=404, detail="Tool response not found")
        return response
    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"[Get Tool Response] Failed to retrieve tool response: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tool response.")