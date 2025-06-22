import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user
from app.database.connection import PostgresConnection
from app.database.learning_profile_queries import (
    has_learning_profile,
    save_learning_profile,
)
from app.schemas.learning_profile import (
    LearningProfileResponse,
    LearningProfileSubmission,
)
from app.schemas.learning_profile_form import LEARNING_PROFILE_FORM
from app.services.profile_desc_generator import generate_learning_profile_description

router = APIRouter(prefix="/learning-profile", tags=["Learning Profile"])


@router.get("/form", status_code=status.HTTP_200_OK)
async def get_learning_profile_form(current_user: str = Depends(get_current_user)):
    return LEARNING_PROFILE_FORM


@router.post("/form", response_model=LearningProfileResponse)
async def submit_learning_profile(
    submission: LearningProfileSubmission, current_user: str = Depends(get_current_user)
):
    try:
        # Aggregate scores
        style_scores = {"Visual": 0, "ReadingWriting": 0, "Kinesthetic": 0}
        count = {k: 0 for k in style_scores}

        for ans in submission.ratings:
            style_scores[ans.style] += ans.score
            count[ans.style] += 1

        avg_scores = {
            k: round(style_scores[k] / count[k], 2)
            for k in style_scores
            if count[k] != 0
        }
        primary_style = max(avg_scores, key=avg_scores.get)

        full_description = await generate_learning_profile_description(
            submission.ratings, submission.mcqs, avg_scores, primary_style
        )

        with PostgresConnection() as conn:
            # TODO - Uncomment the following check after testing
            # exists = has_learning_profile(conn, current_user)

            # if exists:
            #     raise HTTPException(status_code=400, detail="Learning profile already exists for this user")

            save_learning_profile(
                conn=conn,
                user_id=current_user,
                visual=avg_scores.get("Visual", 0),
                reading=avg_scores.get("ReadingWriting", 0),
                kinesthetic=avg_scores.get("Kinesthetic", 0),
                primary_style=primary_style,
                description=full_description,
            )

        return LearningProfileResponse(
            user_id=current_user,
            visual_score=avg_scores.get("Visual", 0),
            reading_score=avg_scores.get("ReadingWriting", 0),
            kinesthetic_score=avg_scores.get("Kinesthetic", 0),
            primary_style=primary_style,
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="Failed to process learning profile"
        )


@router.get("/form/status", status_code=status.HTTP_200_OK)
async def check_learning_profile_status(current_user: str = Depends(get_current_user)):
    try:
        with PostgresConnection() as conn:
            exists = has_learning_profile(conn, current_user)
        return {"submitted": exists}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not verify profile status")
