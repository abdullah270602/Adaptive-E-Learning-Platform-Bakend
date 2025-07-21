import logging
import json
from typing import List
from pydantic import ValidationError
from app.schemas.flashcard import Flashcard
from app.services.constants import KIMI_K2_INSTRUCT
from app.services.models import get_client_for_service
from app.services.prompts import FLASH_CARD_GENERATION_PROMPT, FLASHCARD_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def clean_response_content(raw_content: str) -> str:
    """
    Clean raw response content by removing markdown formatting
    """
    content = raw_content.strip()
    
    # Remove markdown code blocks
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    
    if content.endswith('```'):
        content = content[:-3]
    
    return content.strip()


def validate_flashcards(cards: List[dict]) -> List[dict]:
    """
    Validate flashcard structure using Pydantic
    """
    validated_cards = []

    for i, card in enumerate(cards):
        try:
            validated = Flashcard(**card)
            validated_cards.append(validated.model_dump())
        except ValidationError as e:
            logger.warning(f"Card {i} failed validation: {e.errors()}")

    logger.info(f"Validated {len(validated_cards)} out of {len(cards)} flashcards")
    return validated_cards


async def generate_flashcards(
    content: str,
    title: str,
    chapter_name: str,
    section_name: str,
    learning_profile: str,
    count: int = 5
) -> List[dict]:
    """
    Generate flashcards from the content
    """
    prompt = FLASH_CARD_GENERATION_PROMPT.format(
        title=title,
        chapter_name=chapter_name,
        section_name=section_name,
        learning_profile=learning_profile,
        count=count,
        content=content
    )
    
    client = get_client_for_service("groq")
   
    try:
        response = client.chat.completions.create(
            model= KIMI_K2_INSTRUCT,
            messages=[
                {"role": "system", "content": FLASHCARD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        
        # Clean the response content
        raw_content = response.choices[0].message.content
        cleaned_content = clean_response_content(raw_content)
        
        # Parse JSON safely
        cards = json.loads(cleaned_content)
        
        # Validate structure
        if not isinstance(cards, list):
            logger.error("Response is not a list")
            return []
        
        # Validate and filter cards
        validated_cards = validate_flashcards(cards)
        
        
        return validated_cards
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Raw response: {raw_content}")
        return []
    except Exception as e:
        logger.error(f"Error generating flashcards: {e}")
        return []