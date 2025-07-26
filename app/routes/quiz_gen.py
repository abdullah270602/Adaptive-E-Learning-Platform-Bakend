from fastapi import APIRouter, Depends, Form, status

from app.auth.dependencies import get_current_user
from app.services.mcq_generator import generate_mcq_questions
from app.services.query_processing import expand_user_query_and_search
from app.services.constants import DEFAULT_MODEL_ID  # Import default model ID


router = APIRouter(prefix="/quiz-gen", tags=["Quiz Generation"])


@router.post("/generate-mcqs", status_code=status.HTTP_200_OK)
async def generate_mcqs(
    user_query: str = Form(...),
    difficulty_level: str = Form(...),
    num_mcqs: int = Form(...),  # TODO make pydantic model for RequestBody @izzat
    explanation: bool = Form(...),
    model_id: str = Form(DEFAULT_MODEL_ID),  # Set default directly
    current_user: str = Depends(get_current_user),
):
    try:
        # Call your wrapped function that handles:
        # 1. Expansion
        # 2. Embedding
        # 3. Vector DB Search
        results = await expand_user_query_and_search(
            user_query=user_query,
            user_id=current_user,
            model_id=model_id,
            top_k=5,  # or whatever suits
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

        return {"status": "success", "generated_mcqs": mcq_questions}

    except Exception as e:
        return {"status": "error", "message": str(e)}
