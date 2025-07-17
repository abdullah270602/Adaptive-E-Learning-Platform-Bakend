import json
from typing import Optional
from psycopg2.extensions import connection as PGConnection
import logging

from app.cache.redis import redis_client
from app.services.metadata_utils import get_doc_metadata

logger = logging.getLogger(__name__)



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
