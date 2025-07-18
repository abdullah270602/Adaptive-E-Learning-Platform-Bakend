import json
from fastapi import Depends, APIRouter, HTTPException, Response, status
from app.auth.dependencies import get_current_user
from app.database.connection import PostgresConnection
from app.database.streaks import get_user_streak, update_user_streak

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
