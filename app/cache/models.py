import json
from typing import Optional
from uuid import UUID
from psycopg2.extensions import connection as PGConnection
import logging

from app.cache.redis import redis_client
from app.database.model_queries import get_active_model_name_and_service_by_id, get_all_models_services

logger = logging.getLogger(__name__)


def load_models_to_cache(conn: PGConnection, ttl: int = 3600) -> None:
    """ Load all active models into Redis cache. """
    try:
        models = get_all_models_services(conn)

        for model in models:
            model_id = model["id"]
            key = f"model:{str(model_id)}"
            try:
                redis_client.set(key, json.dumps(model), ttl=ttl)
            except Exception as e:
                logger.warning(f"Failed to set Redis key {key}: {e}")

        logger.info(f"Cached {len(models)} models individually in Redis")
    except Exception as e:
        logger.error(f"Error loading models into Redis: {e}")



def get_active_model_by_id_cached(conn: PGConnection, model_id: UUID) -> Optional[dict]:
    """ Retrieve active model by ID from cache or database."""
    key = f"model:{str(model_id)}"

    # Try from cache
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except json.JSONDecodeError as e:
        logger.warning(f"Corrupted Redis JSON for key {key}: {e}")
    except Exception as e:
        logger.error(f"Redis error fetching {key}: {e}")

    # Fallback to DB
    try:
        model = get_active_model_name_and_service_by_id(conn, model_id)

        if model:
            try:
                redis_client.set(key, json.dumps(model), ttl=3600)
            except Exception as e:
                logger.warning(f"Couldn't cache model {model_id}: {e}")
        return model
    except Exception as e:
        logger.error(f"DB error retrieving model {model_id}: {e}")
        return None