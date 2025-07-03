import json
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from app.auth.dependencies import get_current_user, get_or_create_user
from app.auth.google_auth import oauth, get_google_user_info
from app.auth.utils import create_access_token
from app.database.auth_queries import get_user_by_id
from app.database.connection import PostgresConnection
from app.routes.constants import FRONTEND_DOMAIN

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

@router.get("/google/login")
async def login(request: Request):
    try:
        redirect_uri = request.url_for("auth_callback")
        
        # Extract redirect_origin from query param
        redirect_origin = request.query_params.get("redirect_origin", FRONTEND_DOMAIN)

        # Encode into state (as a JSON string or URL-encoded string)
        state = json.dumps({"redirect_origin": redirect_origin})
        
        return await oauth.google.authorize_redirect(request, redirect_uri, state=state)
    
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


         # Read redirect_origin from OAuth state
        state_str = request.query_params.get("state", "{}")
        try:
            state_data = json.loads(state_str)
        except json.JSONDecodeError:
            state_data = {}

        redirect_origin = state_data.get("redirect_origin", FRONTEND_DOMAIN)

        # if origin is localhost, make cookie less strict
        # is_dev = "localhost" in redirect_origin

        response = RedirectResponse(url=f"{redirect_origin}") # TODO redirect to dashboard or home page
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=False,  # True in prod, False in dev
            secure=False,    # True in prod, False in dev
            samesite="Lax",
            max_age=10080, # 7 days
            path="/"
        )
        logger.info("Setting cookie and redirecting to frontend")
        return response

    except Exception as e:
        logger.exception("Error during OAuth callback")
        raise HTTPException(status_code=500, detail="Authentication failed. Please try again.")


@router.get("/auth/validate")
async def validate_token(user_id: str = Depends(get_current_user)):
    return {"status": "valid", "user_id": user_id}


@router.get("/user")
async def get_user_info(current_user: str = Depends(get_current_user)):
    
    try:
        with PostgresConnection() as conn:
            user = get_user_by_id(conn, current_user)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "id": str(user["id"]),
                "email": user["email"],
                "name": user["name"],
                "profile_pic": user.get("profile_pic", "")
            }
        
    except Exception as e:
        logger.exception("Error retrieving user info")
        raise HTTPException(status_code=500, detail="Failed to retrieve user information")