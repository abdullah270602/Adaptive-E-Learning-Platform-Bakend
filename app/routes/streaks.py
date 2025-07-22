import json
import logging
from fastapi import Depends, APIRouter, HTTPException, Response, status
from app.auth.dependencies import get_current_user
from app.database.connection import PostgresConnection
from app.database.streaks import (
    get_leaderboard_with_user_position,
    get_user_streak,
    update_user_streak,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/streak", tags=["Streaks"])


@router.post("/update", status_code=status.HTTP_201_CREATED)
def update_streak(user_id: str = Depends(get_current_user)):
    """ Update the user's streak based on their activity """
    try:
        with PostgresConnection() as conn:
            result = update_user_streak(conn, user_id)
            if not result["updated"]:
                return Response(
                    status_code=200,
                    content=json.dumps(
                        {
                            "current_streak": result["current_streak"],
                            "updated": result["updated"],
                        }
                    ),
                )
            return result
    except Exception as e:
        return HTTPException(status_code=500, detail="Failed to update streak")


@router.get("", status_code=status.HTTP_200_OK)
def get_user_streak_status(user_id: str = Depends(get_current_user)):
    """ Retrieve the current streak status for the user """
    try:
        with PostgresConnection() as conn:
            data = get_user_streak(conn, user_id)
            return data or {"current_streak": 0, "longest_streak": 0}
    except Exception as e:
        return HTTPException(status_code=500, detail="Failed to get streak status")


@router.get("/leaderboard", status_code=status.HTTP_200_OK)
def get_streak_leaderboard(user_id: str = Depends(get_current_user)):
    """
    Get streak leaderboard showing:
    - Top 5 users
    - Current user position (if not in top 5)
    """
    try:
        with PostgresConnection() as conn:
            leaderboard = get_leaderboard_with_user_position(conn, user_id, limit=5)

            # Format the response
            response = {
                "leaderboard_type": "streak",
                "top_users": [
                    {
                        "rank": user["rank"],
                        "name": user["name"],
                        "current_streak": user["current_streak"],
                        "longest_streak": user["longest_streak"],
                        "is_you": user["user_id"] == user_id,
                    }
                    for user in leaderboard["top_users"]
                ],
                "your_position": {
                    "rank": leaderboard["user_position"]["rank"],
                    "current_streak": leaderboard["user_position"]["current_streak"],
                    "longest_streak": leaderboard["user_position"]["longest_streak"],
                    "show_gap": leaderboard["user_position"]["rank"] > 5,
                },
                "stats": {
                    "total_active_users": leaderboard["total_active_users"],
                    "you_are_top": leaderboard["user_position"]["rank"] <= 5,
                },
            }

            return response

    except Exception as e:
        logger.error(f"Failed to get leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get leaderboard")
