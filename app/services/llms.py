import os
import logging
from typing import List
from openai import OpenAI
from app.schemas.learning_profile import RatingAnswer, MCQAnswer
from app.services.prompts import (
    get_learniing_style_prompt,
    LEARNING_PROFILE_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


async def generate_learning_profile_description(
    ratings: List[RatingAnswer],
    mcqs: List[MCQAnswer],
    avg_scores: dict,
    primary_style: str,
) -> str:
    try:

        # Map behavioral preferences
        behavioral = {q.question: q.answer for q in mcqs}

        prompt = get_learniing_style_prompt(
            answers={
                "ratings": [r.dict() for r in ratings],
                "mcqs": [m.dict() for m in mcqs],
            },
            vrk_scores=avg_scores,
            dominant_styles =primary_style,
            behavioral_prefs=behavioral,
        )

        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=os.getenv("GROQ_BASE_URL"),
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": LEARNING_PROFILE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"[Learning Profile] Failed to generate description: {str(e)}")
        return "Unable to generate learning profile description at this time."
