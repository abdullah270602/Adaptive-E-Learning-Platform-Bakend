import os
import logging
from typing import List
from openai import OpenAI
from app.schemas.learning_profile import RatingAnswer, MCQAnswer
from app.services.prompts import get_learniing_style_prompt, LEARNING_PROFILE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

async def generate_learning_profile_description(
    ratings: List[RatingAnswer],
    mcqs: List[MCQAnswer]
) -> str:
    try:
        # Aggregate VRK scores
        style_scores = {"Visual": 0, "ReadingWriting": 0, "Kinesthetic": 0}
        count = {k: 0 for k in style_scores}
        
        for ans in ratings:
            style_scores[ans.style] += ans.score
            count[ans.style] += 1

        avg_scores = {
            k: round(style_scores[k] / count[k], 2) for k in style_scores if count[k] > 0
        }
        sorted_styles = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        primary_styles = [k for k, v in sorted_styles if v >= sorted_styles[0][1] - 2]

        # Map behavioral preferences
        behavioral = {q.question: q.answer for q in mcqs}

        # Compose prompt
        prompt = get_learniing_style_prompt(
            answers={"ratings": [r.dict() for r in ratings], "mcqs": [m.dict() for m in mcqs]},
            vrk_scores=avg_scores,
            dominant_styles=primary_styles,
            behavioral_prefs=behavioral
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
