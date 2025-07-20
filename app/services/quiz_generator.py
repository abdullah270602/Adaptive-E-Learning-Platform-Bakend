import logging
import json
from pydantic import BaseModel, Field, ValidationError
from typing import List, Literal, Optional
from app.services.constants import KIMI_K2_INSTRUCT
from app.services.models import get_client_for_service
from app.services.prompts import QUIZ_GENERATION_SYSTEM_PROMPT, QUIZ_GENERATION_USER_PROMPT

logger = logging.getLogger(__name__)


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: Optional[List[str]] = Field(default=[])
    correct_answer: str
    explanation: str
    difficulty: Literal[1, 2, 3]
    topic: str
    question_type: Literal["multiple_choice", "true_false", "short_answer"]
    
    
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
            valid.append(QuizQuestion(**item))
        except ValidationError as e:
            logger.warning(f"Invalid quiz question at index {i}: {e}")
    return valid


async def generate_quiz_questions(
    content: str,
    title: str,
    chapter_name: str,
    section_name: str,
    learning_profile: str,
    count: int = 5
) -> List[dict]:
    """
    Generate quiz questions from the given content
    """
    prompt = QUIZ_GENERATION_USER_PROMPT.format(
        title=title or "",
        chapter_name=chapter_name or "",
        section_name=section_name or "",
        learning_profile=learning_profile or "",
        count=count,
        content=content
    )

    client = get_client_for_service("groq")

    try:
        response = client.chat.completions.create(
            model=KIMI_K2_INSTRUCT,
            messages=[
                {"role": "system", "content": QUIZ_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )

        raw_content = response.choices[0].message.content
        cleaned_content = clean_response_content(raw_content)

        questions = json.loads(cleaned_content)

        if not isinstance(questions, list):
            logger.error("Response is not a list of quiz questions")
            return []

        validated_questions = validate_quiz_questions(questions)
        validated_questions_dict = [question.model_dump() for question in validated_questions]
        return validated_questions_dict

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Raw response: {raw_content}")
        return []
    except Exception as e:
        logger.error(f"Error generating quiz questions: {e}")
        return []
