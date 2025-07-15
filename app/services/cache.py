import json
from typing import Optional
from app.services.book_processor import get_doc_metadata
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


def get_cached_doc_metadata(
    conn: PGConnection, document_id: str, document_type: str, ttl: int = 3600
) -> Optional[dict]:
    cache_key = f"doc:{document_type}:{document_id}:metadata"

    try:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to decode cached metadata for key {cache_key}: {e}"
                )
    except Exception as e:
        logger.error(f"Redis error when retrieving {cache_key}: {e}")

    # Cache miss or failure fallback to DB
    try:
        metadata = get_doc_metadata(conn, document_id, document_type)
    except Exception as e:
        logger.error(
            f"DB fallback failed for {document_id} of type {document_type}: {e}"
        )
        return None

    # Cache the result
    if isinstance(metadata, dict):
        try:
            redis_client.set(cache_key, metadata, ttl=ttl)
        except Exception as e:
            logger.error(f"61 Failed to cache metadata for {cache_key}: {e}")
            metadata = get_doc_metadata(conn, document_id, document_type) # DB fall back
    return metadata
