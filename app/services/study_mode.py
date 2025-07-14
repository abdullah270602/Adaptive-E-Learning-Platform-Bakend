from fastapi import HTTPException
import logging
from uuid import UUID, uuid4
from app.database.connection import PostgresConnection
from app.database.study_mode_queries import get_last_chat_messages, insert_chat_messages
from app.schemas.chat import ChatMessageCreate
from app.services.book_processor import get_doc_metadata
from app.services.cache import get_learning_profile_with_cache
from app.services.constants import DEFAULT_MODEL_ID
from app.services.minio_client import MinIOClientContext, get_pdf_bytes_from_minio
from app.services.models import get_reply_from_model
from app.services.prompts import build_chat_message_prompt
from io import BytesIO
import asyncio
import fitz
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_text_from_page(pdf_stream: BytesIO, page_number: int, title: str = "") -> str:
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        if page_number < 0 or page_number >= len(doc):
            raise ValueError(f"Page number {page_number} out of bounds.")
        text = doc[page_number].get_text()
        doc.close()
        
        return {"title": title, "text": text}
    except Exception as e:
        logger.error(f"PDF extraction error: {e}", exc_info=True)
        raise


def get_page_content(document_id: UUID, page_number: int, conn, document_type: str) -> str:
    try:
        metadata = get_doc_metadata(conn, str(document_id), document_type)
        if not metadata or not metadata.get("s3_key"):
            raise ValueError("Missing document metadata or S3 key.")
        with MinIOClientContext() as s3:
            file_stream = get_pdf_bytes_from_minio(s3, metadata["s3_key"])
            return extract_text_from_page(file_stream, page_number, metadata.get("title", ""))
    except Exception as e:
        logger.error(f"Failed to get page content: {e}", exc_info=True)
        raise


async def run_parallel_context_tasks(
    conn, user_id: UUID, document_id: UUID, page_number: int, chat_session_id: UUID
):
    try:
        return await asyncio.gather(
            asyncio.to_thread(get_learning_profile_with_cache, conn, user_id),
            asyncio.to_thread(get_page_content, document_id, page_number, conn, "book"),
            asyncio.to_thread(get_last_chat_messages, conn, chat_session_id),
        )
    except Exception as e:
        logger.error(f"Parallel task execution failed: {e}", exc_info=True)
        raise


def save_user_and_bot_messages(chat_session_id, user_msg, llm_msg, model_id):
    now = datetime.utcnow()
    messages = [
        {
            "id": uuid4(),
            "chat_session_id": str(chat_session_id),
            "role": "user",
            "content": user_msg,
            "model_id": None,
            "tool_type": None,
            "tool_response_id": None,
            "created_at": now,
        },
        {
            "id": uuid4(),
            "chat_session_id": str(chat_session_id),
            "role": "assistant",
            "content": llm_msg,
            "model_id": str(model_id),
            "tool_type": None,
            "tool_response_id": None,
            "created_at": datetime.utcnow(),
        },
    ]

    with PostgresConnection() as conn:
        insert_chat_messages(conn, messages)


async def handle_chat_message(payload: ChatMessageCreate, user_id: UUID) -> str:
    try:
        with PostgresConnection() as conn:
            try:
                learning_profile, title_and_page_content, previous_messages = await run_parallel_context_tasks(
                    conn,
                    user_id,
                    payload.document_id,
                    payload.current_page,
                    payload.chat_session_id
                )
            except Exception as context_error:
                logger.error(f"Error fetching context for chat: {context_error}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to load user context or document.")

        try:
            initial_prompt = build_chat_message_prompt(
                learning_profile,
                title_and_page_content.get("title", ""),
                title_and_page_content["text"],
                payload.content,
                payload.chapter_name,
                payload.section_name,
            )

            # Append history
            history = [{"role": msg["role"], "content": msg["content"]} for msg in previous_messages]
            prompt = [initial_prompt[0]] + history + [initial_prompt[1]]

        except Exception as prompt_error:
            logger.error(f"Prompt building failed: {prompt_error}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to construct model prompt.")

        try:
            reply = get_reply_from_model(str(payload.model_id), prompt)
            return reply

        except Exception as model_error:
            logger.error(f"Model call failed: {model_error}", exc_info=True)
            raise HTTPException(status_code=500, detail="Model generation failed.")

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Unexpected error in handle_chat_message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error while processing chat message.")


