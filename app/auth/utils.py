import os
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"

def create_access_token(user: dict, expires_delta: timedelta = timedelta(minutes=15)) -> str:
    try:
        to_encode = {
            "sub": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "profile_pic": user.get("profile_pic")
        }

        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})

        token = jwt.encode(to_encode, os.getenv("JWT_SECRET_KEY"), algorithm=ALGORITHM)
        return token

    except KeyError as e:
        logger.error(f"Missing user field in JWT payload: {e}")
        raise ValueError(f"Invalid user data for token generation: {e}")

    except JWTError as e:
        logger.error(f"JWT encoding error: {str(e)}")
        raise RuntimeError("Failed to create access token.")

    except Exception as e:
        logger.exception("Unexpected error during JWT creation: ", str(e))
        raise RuntimeError("Internal error creating access token.")


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET_KEY"),
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")]
        )
        return payload
    except ExpiredSignatureError:
        logger.warning("JWT decode failed: token has expired.")
        return None
    except JWTError as e:
        logger.error(f"JWT decode failed: {str(e)}")
        return None
