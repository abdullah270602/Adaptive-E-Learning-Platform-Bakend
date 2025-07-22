import logging
import json
from typing import List
from pydantic import ValidationError
from app.schemas.quiz import QuizQuestion
from app.services.constants import KIMI_K2_INSTRUCT_ID
from app.services.models import get_reply_from_model
from app.services.prompts import QUIZ_GENERATION_SYSTEM_PROMPT, QUIZ_GENERATION_USER_PROMPT

logger = logging.getLogger(__name__)
    
    
def clean_response_content(raw_content: str) -> str:
    """
    Clean raw response content by removing markdown formatting
    """
    content = raw_content.strip()
    
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    
    if content.endswith('```'):
        content = content[:-3]
    
    return content.strip()


def validate_quiz_questions(raw_data: List[dict]) -> List[QuizQuestion]:
    """ Validate quiz questions """
    valid = []
    for i, item in enumerate(raw_data):
        try:
            validated_question = QuizQuestion(**item)
            valid.append(validated_question.model_dump())
        except ValidationError as e:
            logger.warning(f"Invalid quiz question at index {i}: {e}")
    return valid


async def generate_quiz_questions(
    content: str,
    title: str,
    chapter_name: str,
    section_name: str,
    learning_profile: str,
    count: int = 5,
    model_id: str = KIMI_K2_INSTRUCT_ID
) -> List[dict]:
    """
    Generate quiz questions from the given content
    """
    user_prompt = QUIZ_GENERATION_USER_PROMPT.format(
        title=title or "",
        chapter_name=chapter_name or "",
        section_name=section_name or "",
        learning_profile=learning_profile or "",
        count=count,
        content=content,
    )

    try:
        raw_response = get_reply_from_model(
            model_id=model_id,
            chat=[
                {"role": "system", "content": QUIZ_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        cleaned_content = clean_response_content(raw_response)

        questions = json.loads(cleaned_content)

        if not isinstance(questions, list):
            logger.error("Response is not a list of quiz questions")
            return []

        validated_questions = validate_quiz_questions(questions)
        return validated_questions

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Raw response: {raw_response}")
        return []
    except Exception as e:
        logger.error(f"Error generating quiz questions: {e}")
        return []
