import re
from fastapi import HTTPException
import logging
from app.services.constants import LLAMA_3_70b, QWEN_CODER_32b
from app.services.models import get_client_for_service
from app.services.prompts import GAME_CODE_PROMPT, GAME_CODE_PROMPT_OLD, GAME_GEN_SYSTEM_PROMPT, GAME_IDEA_PROMPT
from app.services.utils import get_openai_client


logger = logging.getLogger(__name__)

async def generate_game_stub(content: str, title: str, chapter_name: str, section_name: str, learning_profile: str):
    try:
        return "GAME GEN IN PROGRESS.... 🎰🕹️🎮🎯"
    except Exception as e:
        logger.error(f"Error generating game stub: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating game stub: {str(e)}")
    

async def generate_game_idea(content: str, learning_profile: str,):
    try:
        prompt = GAME_IDEA_PROMPT.format(
            content=content,
            learning_profile=learning_profile
        )
        
        client = get_client_for_service() # TODO ADD service var when implemented
        response = client.chat.completions.create(
            model= "llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert educational game designer. Your task is to generate a game idea based on the given content and learning profile. The game idea should be concise, engaging, and suitable for the target audience. Please ensure that the game idea is unique and not similar to any existing games. You should also provide a brief explanation of the game concept and mechanics. Yor game will idea be used to generate a game code, so it should be detailed enough to allow for code generation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error generating game idea: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating game idea: {str(e)}")


async def generate_game_code(game_idea: str):
    try:
        prompt = GAME_CODE_PROMPT_OLD.format(
            game_idea=game_idea
        )
        
        client = get_client_for_service("huggingface_hyberbolic")
        response = client.chat.completions.create(
            model=QWEN_CODER_32b,
            messages=[
                {"role": "system", "content": GAME_GEN_SYSTEM_PROMPT},
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


async def generate_game(content: str, learning_profile: str):
    """Generate a complete game based on content and learning profile"""
    
    # Generate game idea
    game_idea = await generate_game_idea(content, learning_profile)
    
    # Generate game code
    game_code = await generate_game_code(game_idea)
    
    # Post-process the generated code
    # processed_code = post_process_game_code(game_code)
    
    return {
        "game_idea": game_idea,
        "game_code": game_code
    }