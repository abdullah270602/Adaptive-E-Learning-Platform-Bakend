import json
import re
from typing import Any, Optional, Tuple
from fastapi import HTTPException
import logging
from uuid import UUID, uuid4
from app.cache.learning_profile import get_learning_profile_with_cache
from app.cache.metadata import get_cached_doc_metadata
from app.database.connection import PostgresConnection
from app.database.study_mode_queries import get_last_chat_messages, insert_chat_messages, insert_tool_response
from app.schemas.chat import ChatMessageCreate
from app.services.diagram_generator import generate_diagrams
from app.services.flashcard_generator import generate_flashcards
from app.services.game_generator import generate_game_stub
from app.services.minio_client import MinIOClientContext, get_pdf_bytes_from_minio
from app.services.models import get_reply_from_model
from app.services.prompts import build_chat_message_prompt
from io import BytesIO
import asyncio
import fitz
from datetime import datetime

from app.services.quiz_generator import generate_quiz_questions

logger = logging.getLogger(__name__)

LEARNING_TOOLS_WITH_PARAMS = {
    "diagram": lambda content, title, chapter_name, section_name, learning_profile: generate_diagrams(
        content, title, chapter_name, section_name, learning_profile
    ),
    "game": lambda content, title, chapter_name, section_name, learning_profile: generate_game_stub(
        content, title, chapter_name, section_name, learning_profile
    ),
    "flashcard": lambda content, title, chapter_name, section_name, learning_profile, count=5: generate_flashcards(
        content, title, chapter_name, section_name, learning_profile, count
    ),
    "quiz": lambda content, title, chapter_name, section_name, learning_profile, count=5: generate_quiz_questions(
        content, title, chapter_name, section_name, learning_profile, count
    ),
}


def extract_text_from_page(pdf_stream: BytesIO, page_number: int, title: str = "") -> dict:
    """Extract text and metadata from a specific page of a PDF document."""
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        if page_number < 0 or page_number >= len(doc):
            raise ValueError(f"Page number {page_number} out of bounds.")
        
        page = doc[page_number]
        text = page.get_text()
        images = page.get_images(full=False)
        image_count = len(images)
        
        if image_count > 0 and not text.strip():
            note = "This page contains one or more diagrams/images but no readable text."

        doc.close()
        return {
            "title": title,
            "text": text,
            "image_count": image_count,
        }

    except Exception as e:
        logger.error(f"PDF extraction error: {e}", exc_info=True)
        raise


def get_page_content(
    document_id: UUID, page_number: int, conn, document_type: str
) -> str:
    """Retrieve the content of a specific page from a document."""
    try:
        metadata = get_cached_doc_metadata(conn, str(document_id), document_type)
        if not metadata or not metadata.get("s3_key"):
            raise ValueError("Missing document metadata or S3 key.")
        with MinIOClientContext() as s3:
            file_stream = get_pdf_bytes_from_minio(s3, metadata["s3_key"])
            return extract_text_from_page(
                file_stream, page_number, metadata.get("title", "")
            )
    except Exception as e:
        logger.error(f"Failed to get page content: {e}", exc_info=True)
        raise


async def run_parallel_context_tasks(
    conn, user_id: UUID, document_id: UUID, documnet_type: str, page_number: int, chat_session_id: UUID
):
    """Run parallel tasks to fetch user learning profile, page content, and last chat messages."""
    try:
        return await asyncio.gather(
            asyncio.to_thread(get_learning_profile_with_cache, conn, user_id),
            asyncio.to_thread(get_page_content, document_id, page_number, conn, documnet_type),
            asyncio.to_thread(get_last_chat_messages, conn, chat_session_id),
        )
    except Exception as e:
        logger.error(f"Parallel task execution failed: {e}", exc_info=True)
        raise


def save_interaction_to_db(chat_session_id, user_msg, llm_msg, model_id, tool_name, tool_response_id, tool_response):
    """Save user and bot messages to the database."""
    now = datetime.utcnow()
    
    with PostgresConnection() as conn:
        try:
            # First insert tool response if exists
            if tool_response_id and tool_response:
                saved_tool_response_id = insert_tool_response(
                    conn, tool_response_id, tool_name, tool_response, tool_response
                )
                if not saved_tool_response_id:
                    raise Exception(f"Failed to insert tool response with id {tool_response_id}")
            
            # Then insert messages
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
                    "tool_type": tool_name,
                    "tool_response_id": str(tool_response_id) if tool_response_id else None,
                    "created_at": datetime.utcnow(),
                }
            ]
            
            insert_chat_messages(conn, messages)
            
            # Commit the transaction after both operations
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        

def detect_tool_and_clean_reply(reply: str) -> Tuple[Optional[dict], str]:
    """
    Detects simple tool call in the format:
        TOOL_CALL: {"tool": "tool_name"}

    Returns:
        - tool_info: {"tool_name": <tool>} if found, else None
        - cleaned_reply: reply with TOOL_CALL block removed
    """
    tool_info = None
    cleaned_reply = reply
    
    try:
        match = re.search(r"TOOL_CALL:\s*(\{.*?\})", reply.strip(), re.DOTALL)
        if match:
            raw_json = match.group(1)
            cleaned_reply = reply.replace(match.group(0), "").strip()

            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict) and "tool" in parsed:
                    tool_info = {"tool_name": parsed["tool"]}
            except json.JSONDecodeError as e:
                print(f"[Tool Parse Failed] {e} → raw: {raw_json}")

    except Exception as e:
        print(f"[Tool Detection Error] {e}")

    return tool_info, cleaned_reply


async def run_tool(tool_name: str, context: dict) -> Optional[Any]:  # TODO make this async
    try:
        if tool_name not in LEARNING_TOOLS_WITH_PARAMS:
            return {"error": f"Tool '{tool_name}' not found"}
    
        tool = LEARNING_TOOLS_WITH_PARAMS[tool_name.lower()](**context)
        return await tool
        
    except Exception as e:
        logger.error(f"Error running tool {tool_name}: {e}", exc_info=True)
        return None


async def handle_chat_message(payload: ChatMessageCreate, user_id: UUID) -> str:
    """Handle a chat message by fetching context, building a prompt, getting a reply from the mode and running tools."""
    try:
        with PostgresConnection() as conn:
            try:
                learning_profile, title_and_page_content, previous_messages = (
                    await run_parallel_context_tasks(
                        conn,
                        user_id,
                        payload.document_id,
                        payload.document_type,
                        payload.current_page,
                        payload.chat_session_id,
                    )
                )
                logger.info("Parallel tasks completed successfully.")

                context_for_tool = {
                    "content": title_and_page_content["text"],
                    "title": title_and_page_content.get("title", ""),
                    "chapter_name": payload.chapter_name,
                    "section_name": payload.section_name,
                    "learning_profile": learning_profile,
                }
            except Exception as context_error:
                logger.error(
                    f"Error fetching context for chat: {context_error}", exc_info=True
                )
                raise HTTPException(
                    status_code=500, detail="Failed to load user context or document."
                )

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
            history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in previous_messages
            ]
            prompt = [initial_prompt[0]] + history + [initial_prompt[1]]

        except Exception as prompt_error:
            logger.error(f"Prompt building failed: {prompt_error}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Failed to construct model prompt."
            )

        try:
            reply = get_reply_from_model(str(payload.model_id), prompt) # TODO Un comment after testing 🚨🚨🚨
            # reply = "THIS IS A TEST REPLY xyz \n \n ..... TOOL_CALL: {\"tool\": \"quiz\"} ....."

            # Detect tool trigger and clean reply if found
            detected_tool, cleaned_reply = detect_tool_and_clean_reply(reply)

            if detected_tool:
                logger.info(f"Tool detected: {detected_tool['tool_name']}")

                try:
                    tool_raw_result = await run_tool(detected_tool["tool_name"], context_for_tool)

                    # final response dict
                    final_response = {
                        "llm_reply": cleaned_reply,
                        "tool_name": detected_tool["tool_name"],
                        "tool_response": tool_raw_result,
                    }
                    
                except Exception as tool_error:
                    logger.error(f"Tool execution failed: {tool_error}", exc_info=True)
                    raise HTTPException(
                        status_code=500, detail="Tool execution failed."
                    )

            else:
                final_response = {"llm_reply": reply, "tool_name": None, "tool_response": None}

            return final_response

        except Exception as model_error:
            logger.error(
                f"Model call or tool handling failed: {model_error}", exc_info=True
            )
            raise HTTPException(status_code=500, detail="Model processing failed.")

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Unexpected error in handle_chat_message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Unexpected error while processing chat message."
        )
