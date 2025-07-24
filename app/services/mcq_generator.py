from app.services.prompts import EXPLANATION_CONFIGS, INSTRUCTION_MAPPING,DIFFICULTY_MAPPING,MCQ_GEN_SYSTEM_PROMPT,MIXED_DIFFICULTY_INSTRUCTIONS,EASY_DIFFICULTY_INSTRUCTIONS,MEDIUM_DIFFICULTY_INSTRUCTIONS,MCQ_GEN_USER_PROMPT
import json
from app.services.models import get_reply_from_model
from app.services.quiz_generator import clean_response_content
from typing import List





async def generate_mcq_questions(
    content: str,
    difficulty_level: str,
    num_mcqs: int,
    explanation: bool,
    topic: str,
    model_id: str
) -> List[dict]:
    """
    Generate MCQ questions from the given content
    
    Args:
        content (str): The chunk text to generate questions from
        difficulty_level (str): Difficulty level ("easy", "medium", "hard", "mixed")
        num_mcqs (int): Number of MCQs to generate (default: 5)
        explanation (bool): Whether to include explanations (True/False)
        topic (str): Topic name for the questions (default: "General")
        model_id (str): Model ID to use for generation
    
    Returns:
        List[dict]: List of generated MCQ questions
    """
    # Get explanation configuration
    explanation_key = "with_explanations" if explanation else "without_explanations"
    explanation_config = EXPLANATION_CONFIGS[explanation_key]
    
    # Get difficulty instructions
    difficulty_instructions = INSTRUCTION_MAPPING.get(difficulty_level.lower(), MEDIUM_DIFFICULTY_INSTRUCTIONS)
    difficulty_number = DIFFICULTY_MAPPING.get(difficulty_level.lower(), 2)
    
    # Format difficulty instructions with explanation notes
    formatted_difficulty_instructions = difficulty_instructions.format(
        EXPLANATION_DIFFICULTY_NOTE=explanation_config["EXPLANATION_DIFFICULTY_NOTE"]
    )
    
    # Format system prompt
    system_prompt = MCQ_GEN_SYSTEM_PROMPT.format(
        EXPLANATION_INSTRUCTION=explanation_config["EXPLANATION_INSTRUCTION"],
        DIFFICULTY_LEVEL=difficulty_level,
        DIFFICULTY_SPECIFIC_INSTRUCTIONS=formatted_difficulty_instructions
    )
    
    # Format user prompt
    user_prompt = MCQ_GEN_USER_PROMPT.format(
        TOPIC=topic,
        DIFFICULTY_LEVEL=difficulty_level,
        K=num_mcqs,
        CONTENT=content,
        EXPLANATION_FIELD=explanation_config["EXPLANATION_FIELD"],
        DIFFICULTY_NUMBER=difficulty_number
    )

    try:
        raw_response = get_reply_from_model(
            model_id=model_id,
            chat=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        cleaned_content = clean_response_content(raw_response)
        questions = json.loads(cleaned_content)
        
        return questions

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return []
    except Exception as e:
        print(f"Error generating MCQ questions: {e}")
        return []