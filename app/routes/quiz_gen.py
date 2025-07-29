from fastapi import APIRouter, Depends, Form, status,HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import io
from fastapi import Response
from app.auth.dependencies import get_current_user
from app.services.mcq_generator import generate_mcq_questions
from app.services.query_processing import expand_user_query_and_search
from app.services.constants import DEFAULT_MODEL_ID  # Import default model ID
from app.database.mcq_queries import save_user_quiz,get_user_latest_quiz,get_user_quiz,save_quiz_history,get_quiz_history,get_user_quiz_history
from app.database.connection import PostgresConnection
from app.services.download_file import create_docx,create_pdf
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz-gen", tags=["Quiz Generation"])

@router.post("/", status_code=status.HTTP_200_OK)
async def generate_mcqs(
    user_query: str = Form(...),
    difficulty_level: str = Form(...),
    num_mcqs: int = Form(...),  # TODO make pydantic model for RequestBody @izzat
    explanation: bool = Form(...),
    model_id: str = Form(DEFAULT_MODEL_ID),  # Set default directly
    doc_ids: Optional[str] = Form(None),  # New parameter for document filtering
    file_type: Optional[str] = Form(None),  # New parameter for download functionality
    current_user: str = Depends(get_current_user),
):
    try:
        # Call your wrapped function that handles:
        # 1. Expansion
        # 2. Embedding
        # 3. Vector DB Search
        logger.info(f"[user_query]: {user_query}, model_id: {model_id}, doc_ids: {doc_ids}, doc_type: {file_type}")
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

        # If file_type is provided, return the file for download
        if file_type:
            try:
                # Generate the file
                if file_type.lower() == "pdf":
                    file_buffer = create_pdf(mcq_questions)
                    filename = f"mcqs_{current_user}_{quiz_id}.pdf"
                    media_type = "application/pdf"

                elif file_type.lower() == "docx":
                    file_buffer = create_docx(mcq_questions)
                    filename = f"mcqs_{current_user}_{quiz_id}.docx"
                    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                else:
                    # If invalid file type, return JSON response with error
                    return {
                        "status": "error",
                        "message": "Invalid file type. Supported types: pdf, docx",
                        "generated_mcqs": mcq_questions,
                        "quiz_id": quiz_id
                    }

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

            except Exception as download_error:
                # If download fails, return JSON response with the MCQs
                return {
                    "status": "partial_success",
                    "message": f"MCQs generated successfully but download failed: {str(download_error)}",
                    "generated_mcqs": mcq_questions,
                    "quiz_id": quiz_id
                }

        # If no file_type provided, return JSON response as before
        return {
            "status": "success", 
            "generated_mcqs": mcq_questions,
            "quiz_id": quiz_id
        }

    except Exception as e:
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
        print(f"DEBUG: Error in /download-mcqs: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    

@router.post("/quiz-history", status_code=status.HTTP_200_OK)
async def save_quiz_history_endpoint(
    quiz_id: str = Form(...),  # Changed from int to str for UUID
    doc_id: str = Form(...),   # Changed from int to str for UUID
    doc_name: str = Form(...),
    score: str = Form(...),  # e.g., "8/10"
    accuracy: float = Form(...),  # e.g., 80.0
    quiz_data: str = Form(...),  # JSON string of quiz data
    current_user: str = Depends(get_current_user),
):
    try:
        logger.info(f"Saving quiz history for user: {current_user}, quiz_id: {quiz_id}, score: {score}")
        
        # Parse quiz_data from JSON string to list
        try:
            quiz_data_parsed = json.loads(quiz_data)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "Invalid JSON format for quiz_data",
            }
        
        # Save quiz history to database
        history_id = None
        with PostgresConnection() as conn:
            history_id = save_quiz_history(
                conn=conn,
                user_id=current_user,
                quiz_id=quiz_id,
                doc_id=doc_id,
                doc_name=doc_name,
                score=score,
                accuracy=accuracy,
                quiz_data=quiz_data_parsed
            )
        
        logger.info(f"Quiz history saved successfully with ID: {history_id}")
        
        return {
            "status": "success",
            "message": "Quiz history saved successfully",
            "history_id": history_id,
            "data": {
                "quiz_id": quiz_id,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "score": score,
                "accuracy": accuracy,
                "user_id": current_user
            }
        }
        
    except Exception as e:
        logger.error(f"Error saving quiz history: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to save quiz history: {str(e)}",
        }
    

@router.get("/quiz-history/{history_id}", status_code=status.HTTP_200_OK)
async def get_quiz_history_endpoint(
    history_id: str,
    current_user: str = Depends(get_current_user),
):
    try:
        logger.info(f"Retrieving quiz history for user: {current_user}, history_id: {history_id}")
        
        # Retrieve quiz history from database
        quiz_history = None
        with PostgresConnection() as conn:
            quiz_history = get_quiz_history(
                conn=conn,
                history_id=history_id
            )
        
        if quiz_history is None:
            logger.warning(f"Quiz history not found for ID: {history_id}")
            return {
                "status": "error",
                "message": "Quiz history not found",
            }
        
        # Check if the quiz history belongs to the current user
        if quiz_history["user_id"] != current_user:
            logger.warning(f"Unauthorized access attempt by user {current_user} for history {history_id}")
            return {
                "status": "error",
                "message": "Unauthorized access to quiz history",
            }
        
        logger.info(f"Quiz history retrieved successfully for ID: {history_id}")
        
        return {
            "status": "success",
            "message": "Quiz history retrieved successfully",
            "data": quiz_history
        }
        
    except Exception as e:
        logger.error(f"Error retrieving quiz history: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to retrieve quiz history: {str(e)}",
        }


@router.get("/user-quiz-history", status_code=status.HTTP_200_OK)
async def get_user_quiz_history_endpoint(
    current_user: str = Depends(get_current_user),
):
    try:
        logger.info(f"Retrieving quiz history list for user: {current_user}")
        
        # Retrieve all quiz history for the user
        user_quiz_history = []
        with PostgresConnection() as conn:
            user_quiz_history = get_user_quiz_history(
                conn=conn,
                user_id=current_user
            )
        
        logger.info(f"Retrieved {len(user_quiz_history)} quiz records for user: {current_user}")
        
        return {
            "status": "success",
            "message": f"Retrieved {len(user_quiz_history)} quiz records",
            "total_quizzes": len(user_quiz_history),
            "data": user_quiz_history
        }
        
    except Exception as e:
        logger.error(f"Error retrieving user quiz history: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to retrieve quiz history: {str(e)}",
        }