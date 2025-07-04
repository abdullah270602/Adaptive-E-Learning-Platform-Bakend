import re
from fastapi import HTTPException
import logging

from app.services.constants import LLAMA_3_70b
from app.services.prompts import GAME_CODE_PROMPT, GAME_CODE_PROMPT_OLD, GAME_IDEA_PROMPT
from app.services.utils import get_openai_client


logger = logging.getLogger(__name__)

def generate_game_idea(content: str, learning_profile: str,):
    try:
        prompt = GAME_IDEA_PROMPT.format(
            content=content,
            learning_profile=learning_profile
        )
        
        client = get_openai_client()
        response = client.chat.completions.create(
            model= LLAMA_3_70b,
            messages=[
                {"role": "system", "content": "You are an expert educational game designer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error generating game idea: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating game idea: {str(e)}")


def generate_game_code(game_idea: str):
    try:
        prompt = GAME_CODE_PROMPT_OLD.format(
            game_idea
        )
        
        client = get_openai_client()
        response = client.chat.completions.create(
            model=LLAMA_3_70b,
            messages=[
                {"role": "system", "content": "You are an expert educational game developer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"Error generating game code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating game code: {str(e)}")
    

def post_process_game_code(code):
    """Enhanced post-processing to catch JSX and other issues"""
    if not code:
        raise ValueError("Generated code is empty")

    # Remove any accidental wrapper functions
    code = re.sub(r'^return\s*function\s*\w*\s*\(\)\s*{', '', code)
    code = re.sub(r'}\s*$', '', code)
    
    # Check for JSX and reject if found
    if re.search(r'<\w+', code) or re.search(r'</\w+>', code):
        raise ValueError("JSX syntax detected - code must use React.createElement only")
    
    # Fix common semicolon issues
    code = re.sub(r'({[^}]+});(?=\s*[}\]])', r'\1', code)
    code = re.sub(r'(}\s*);(\s*else|\s*[)\]])', r'\1\2', code)
    
    # Ensure useState has default values
    code = re.sub(r'useState\(\s*\)', 'useState(null)', code)
    
    # Check for className usage (should be fine in React.createElement)
    jsx_classname = re.search(r'className\s*=\s*["\'][^"\']*["\'](?![^{]*})', code)
    if jsx_classname:
        raise ValueError("JSX className syntax detected - use React.createElement format")
    
    return code.strip()


def generate_game(content: str, learning_profile: str):
    """Generate a complete game based on content and learning profile"""
    
    # Generate game idea
    game_idea = generate_game_idea(content, learning_profile)
    print("🐍 File: services/game_generatory.py | Line: 92 | generate_game ~ game_idea",game_idea)
    
    # Generate game code
    game_code = generate_game_code(game_idea)
    print("🐍 File: services/game_generatory.py | Line: 96 | generate_game ~ game_code",game_code)
    
    # Post-process the generated code
    # processed_code = post_process_game_code(game_code)
    
    return {
        "game_idea": game_idea,
        "game_code": game_code
    }