from fastapi import APIRouter, Depends, Form, status, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import io
from fastapi import Response
from app.auth.dependencies import get_current_user
from app.services.mcq_generator import generate_mcq_questions
from app.services.query_processing import expand_user_query_and_search
from app.services.constants import DEFAULT_MODEL_ID  # Import default model ID
from app.database.mcq_queries import save_user_quiz, get_user_latest_quiz, get_user_quiz
from app.database.connection import PostgresConnection
from app.services.downloadfile import create_docx, create_pdf
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz-gen", tags=["Quiz Generation"])

@router.post("/", status_code=status.HTTP_200_OK)
async def generate_mcqs(
    user_query: str = Form(...),
    difficulty_level: str = Form(...),
    num_mcqs: int = Form(...),  # TODO make pydantic model for RequestBody @izzat
    explanation: bool = Form(...),
    download_file: bool = Form(False),  # NEW: Boolean condition for file download
    file_type: str = Form("pdf"),  # NEW: File type for download (pdf/docx)
    model_id: str = Form(DEFAULT_MODEL_ID),  # Set default directly
    doc_ids: Optional[str] = Form(None),  # New parameter for document filtering
    current_user: str = Depends(get_current_user),
):
    try:
        # Call your wrapped function that handles:
        # 1. Expansion
        # 2. Embedding
        # 3. Vector DB Search
        logger.info(f"[user_query]: {user_query}, model_id: {model_id}, doc_ids: {doc_ids}, download_file: {download_file}, file_type: {file_type}")
        results = await expand_user_query_and_search(
            user_query=user_query,
            user_id=current_user,
            model_id=model_id,
            top_k=5,  # or whatever suits if the chunks are less than 5 then what ?
            doc_ids=doc_ids,  # Pass the document IDs directly
        )

        if results is None:
            return {
                "status": "error",
                "message": "Failed to retrieve relevant content.",
            }

        # Extract chunk texts from results
        chunk_texts = [chunk["text"] for chunk in results]
        combined_content = "\n\n".join(chunk_texts)

        # Generate MCQs using the retrieved content
        mcq_questions = await generate_mcq_questions(
            content=combined_content,
            difficulty_level=difficulty_level,
            num_mcqs=num_mcqs,
            explanation=explanation,
            model_id=model_id,
        )
        logger.info(f"Generated MCQs: {json.dumps(mcq_questions, indent=2)}")
        
        # Save MCQs to database
        quiz_id = None
        with PostgresConnection() as conn:
            # Parse doc_ids if provided (assuming it might be comma-separated)
            doc_id = doc_ids.split(',')[0] if doc_ids else None
            
            quiz_id = save_user_quiz(
                conn=conn,
                user_id=current_user,
                doc_id=doc_id,
                num_mcqs=num_mcqs,
                mcq_data=mcq_questions
            )

        # NEW: Check boolean condition for response type
        if download_file:
            # Return streaming file response
            try:
                if not mcq_questions or len(mcq_questions) == 0:
                    raise HTTPException(status_code=400, detail="No MCQs generated for download")

                # Validate and normalize file_type
                file_type_lower = file_type.lower().strip()
                if file_type_lower not in ["pdf", "docx"]:
                    raise HTTPException(status_code=400, detail="Invalid file type. Use 'pdf' or 'docx'")

                # Generate the file based on file_type
                if file_type_lower == "pdf":
                    logger.info(f"Generating PDF with {len(mcq_questions)} MCQs")
                    file_buffer = create_pdf(mcq_questions)
                    filename = f"mcqs_{current_user}_{quiz_id}.pdf"
                    media_type = "application/pdf"
                    
                elif file_type_lower == "docx":
                    logger.info(f"Generating DOCX with {len(mcq_questions)} MCQs")
                    file_buffer = create_docx(mcq_questions)
                    filename = f"mcqs_{current_user}_{quiz_id}.docx"
                    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                # Ensure buffer is at the start and has content
                if not file_buffer:
                    raise HTTPException(status_code=500, detail="File buffer is empty")
                
                file_buffer.seek(0)
                buffer_size = len(file_buffer.getvalue())
                logger.info(f"Generated {file_type_lower.upper()} file: {filename}, size: {buffer_size} bytes")

                if buffer_size == 0:
                    raise HTTPException(status_code=500, detail="Generated file is empty")

                return StreamingResponse(
                    io.BytesIO(file_buffer.getvalue()),  # Create a new buffer to avoid any issues
                    media_type=media_type,
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Content-Length": str(buffer_size),
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
                
            except HTTPException:
                raise
            except ValueError as ve:
                logger.error(f"Validation error in file generation: {ve}")
                raise HTTPException(status_code=400, detail=str(ve))
            except RuntimeError as re:
                logger.error(f"Runtime error in file generation: {re}")
                raise HTTPException(status_code=500, detail=str(re))
            except Exception as file_error:
                logger.error(f"Unexpected error in file generation: {file_error}")
                raise HTTPException(status_code=500, detail=f"File generation failed: {str(file_error)}")
        else:
            # Return JSON response (original behavior)
            return {
                "status": "success", 
                "generated_mcqs": mcq_questions,
                "quiz_id": quiz_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_mcqs: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/download-mcqs")
async def download_mcqs(
    file_type: str = Form(...),
    quiz_id: str = Form(None),
    current_user: str = Depends(get_current_user)
):
    quiz_id = quiz_id.strip() 
    try:
        with PostgresConnection() as conn:
            if quiz_id:
                quiz_data = get_user_quiz(conn, quiz_id, current_user)
                if not quiz_data:
                    raise HTTPException(status_code=404, detail="Quiz not found")
            else:
                quiz_data = get_user_latest_quiz(conn, current_user)
                if not quiz_data:
                    raise HTTPException(status_code=404, detail="No quizzes found for user")

            mcqs = quiz_data.get('mcq_data')
            if not mcqs or len(mcqs) == 0:
                raise HTTPException(status_code=400, detail="No MCQs found in the quiz")

        # Generate the file
        if file_type.lower() == "pdf":
            file_buffer = create_pdf(mcqs)
            filename = f"mcqs_{current_user}_{quiz_data['id']}.pdf"
            media_type = "application/pdf"

        elif file_type.lower() == "docx":
            file_buffer = create_docx(mcqs)
            filename = f"mcqs_{current_user}_{quiz_data['id']}.docx"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        else:
            raise HTTPException(status_code=400, detail="Invalid file type")

        file_buffer.seek(0)  # Ensure correct start

        return StreamingResponse(
            file_buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /download-mcqs: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")