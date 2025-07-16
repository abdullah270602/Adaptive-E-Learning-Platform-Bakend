import json
import re
from typing import Any, Optional, Tuple
from fastapi import HTTPException
import logging
from uuid import UUID, uuid4
from app.database.connection import PostgresConnection
from app.database.study_mode_queries import get_last_chat_messages, insert_chat_messages
from app.schemas.chat import ChatMessageCreate
from app.services.cache import get_cached_doc_metadata, get_learning_profile_with_cache
from app.services.minio_client import MinIOClientContext, get_pdf_bytes_from_minio
from app.services.models import get_reply_from_model
from app.services.prompts import build_chat_message_prompt
from io import BytesIO
import asyncio
import fitz
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_text_from_page(pdf_stream: BytesIO, page_number: int, title: str = "") -> str:
    """ Extract text from a specific page of a PDF document."""
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
    """ Retrieve the content of a specific page from a document."""
    try:
        metadata = get_cached_doc_metadata(conn, str(document_id), document_type)
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
    """ Run parallel tasks to fetch user learning profile, page content, and last chat messages."""
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
    """ Save user and bot messages to the database."""
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
        match = re.search(r'TOOL_CALL:\s*(\{.*?\})', reply.strip(), re.DOTALL)
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


def run_tool(tool_name: str) -> Optional[Any]:  # TODO make this async
    try:
        return {
            "diagrams": [
                "graph TD\n    LogicalThinking  -->  BuildingBlocks\n    BuildingBlocks  -->  ProblemSolvingSkills\n    ProblemSolvingSkills  -->  BetterProgramming",
                "graph TD\n    CurrentSkillLevel  -->  ImproveSkillLevel\n    ImproveSkillLevel  -->  NewKnowledge\n    NewKnowledge  -->  EnhancedProblemSolving",
                "graph TD\n    ConceptUnderstanding  -->  ClearInstructions\n    ClearInstructions  -->  FocusAndRetention\n    FocusAndRetention  -->  DeepUnderstanding",
            ]
        }
    except Exception as e:
        logger.error(f"Error running tool {tool_name}: {e}", exc_info=True)
        return None


def clean_tool_response(tool_name: str, tool_result: Any, original_reply: str) -> str:
    """
    Optionally strip tool trigger from original reply and append formatted tool result.
    """
    
    return {"tool_name": tool_name, "tool_response": tool_result, "llm_reply": original_reply}


async def handle_chat_message(payload: ChatMessageCreate, user_id: UUID) -> str:
    """ Handle a chat message by fetching context, building a prompt, getting a reply from the mode and running tools."""
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
                logger.info("Parallel tasks completed successfully.")
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

            # Detect tool trigger and clean reply if found
            detected_tool, cleaned_reply = detect_tool_and_clean_reply(reply)

            if detected_tool:
                logger.info(f"Tool detected: {detected_tool['tool_name']}")

                try:
                    tool_raw_result = run_tool(detected_tool['tool_name'])

                    final_response = clean_tool_response(
                        tool_name=detected_tool["tool_name"],
                        tool_result=tool_raw_result,
                        original_reply=cleaned_reply +"\n\n                                       ________________ORIGINAL REPLY_______: \n"+ reply
                    )
                except Exception as tool_error:
                    logger.error(f"Tool execution failed: {tool_error}", exc_info=True)
                    raise HTTPException(status_code=500, detail="Tool execution failed.")

            else:
                final_response = cleaned_reply

            return final_response

        except Exception as model_error:
            logger.error(f"Model call or tool handling failed: {model_error}", exc_info=True)
            raise HTTPException(status_code=500, detail="Model processing failed.")

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Unexpected error in handle_chat_message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error while processing chat message.")
