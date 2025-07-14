import json
from app.services.redis_client import redis_client
from app.database.learning_profile_queries import get_learning_profile_by_user
from psycopg2.extensions import connection as PGConnection
import logging

logger = logging.getLogger(__name__)

def get_learning_profile_with_cache(conn: PGConnection, user_id: str, ttl: int = 3600) -> dict | None:
    cache_key = f"user:{user_id}:learning_profile"

    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        profile = get_learning_profile_by_user(conn, str(user_id))
        if profile:
            redis_client.set(cache_key, profile, ttl=ttl)
        return profile
    except Exception as e:
        # fallback to DB even if cache fails
        logger.error(f"Failed to get learning profile from cache: {e}")
        return get_learning_profile_by_user(conn, str(user_id))
