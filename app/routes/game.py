from fastapi import APIRouter, HTTPException
import logging
from fastapi.params import Depends
from app.auth.dependencies import get_current_user
from app.database.connection import PostgresConnection
from app.database.learning_profile_queries import get_learning_profile_by_user
from app.schemas.game import GameRequest
from app.services.game_generator import generate_game

router = APIRouter(prefix="/game", tags=["Game"])

logger = logging.getLogger(__name__)


@router.post("/generate")
async def generate_game_endpoint(
    request: GameRequest,
    current_user: str = Depends(get_current_user),
):
    try:
        with PostgresConnection() as conn:
            learning_profile = get_learning_profile_by_user(conn, current_user)
            if not learning_profile:
                raise HTTPException(status_code=404, detail="Learning profile not found")
            
        game = await generate_game(request.content, learning_profile)
        return {"game": game}
    
    except Exception as e:
        logger.error(f"Error generating game: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate game")