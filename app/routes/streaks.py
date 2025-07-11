from fastapi import Depends, APIRouter, HTTPException, status
from app.auth.dependencies import get_current_user
from app.database.connection import PostgresConnection
from app.database.streaks import get_user_streak, update_user_streak

router = APIRouter(prefix="/streak", tags=["Streaks"])

@router.post("/update", status_code=status.HTTP_201_CREATED)
def update_streak(user_id: str = Depends(get_current_user)):
    try:
        with PostgresConnection() as conn:
            result = update_user_streak(conn, user_id)
            print("🐍 File: routes/streaks.py | Line: 13 | update_streak ~ result",result)
            return {
                "current_streak": result["current_streak"],
                "updated": result["updated"]
            }
    except Exception as e:
        return HTTPException(status_code=500, detail="Failed to update streak")

@router.get("", status_code=status.HTTP_200_OK)
def get_user_streak_status(user_id: str = Depends(get_current_user)):
    try:
        with PostgresConnection() as conn:
            data = get_user_streak(conn, user_id)
            return data or {"current_streak": 0, "longest_streak": 0}
    except Exception as e:
        return HTTPException(status_code=500, detail="Failed to get streak status")