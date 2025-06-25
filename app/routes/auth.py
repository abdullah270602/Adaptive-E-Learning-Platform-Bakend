import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from app.auth.dependencies import get_current_user, get_or_create_user
from app.auth.google_auth import oauth, get_google_user_info
from app.auth.utils import create_access_token
from app.database.connection import PostgresConnection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

@router.get("/google/login")
async def login(request: Request):
    try:
        redirect_uri = request.url_for("auth_callback")
        return await oauth.google.authorize_redirect(request, redirect_uri)
    
    except Exception as e:
        logger.exception("Error during Google login redirect")
        raise HTTPException(status_code=500, detail="Google login failed. Please try again.")


@router.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        user_info = await get_google_user_info(request)
        email = user_info["email"]
        name = user_info.get("name", "")
        picture = user_info.get("picture", "")

        with PostgresConnection() as conn:
            user = get_or_create_user(conn, email, name, picture)

        sanitized_user = {
            "id": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "profile_pic": user_info.get("picture", "")

        }

        token = create_access_token(sanitized_user)

        return {
            "access_token": token,
            "token_type": "bearer",
        }

        # TODO Respond with set_cookie header for security

    except Exception as e:
        logger.exception("Error during OAuth callback")
        raise HTTPException(status_code=500, detail="Authentication failed. Please try again.")


@router.get("/auth/validate")
async def validate_token(user_id: str = Depends(get_current_user)):
    return {"status": "valid", "user_id": user_id}