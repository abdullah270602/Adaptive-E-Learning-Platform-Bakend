import json
import redis
import os
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(
        self,
        host=os.getenv("REDIS_HOST", "localhost"),
        port=os.getenv("REDIS_PORT"),
        password=os.getenv("REDIS_PASSWORD"),
        db=0,
        decode_responses=True,
    ):
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=decode_responses,
            )
            # Test connection
            self.client.ping()
            logger.info("Redis connection established.")
        except redis.exceptions.ConnectionError as e:
            logger.critical(" Redis connection failed: %s", str(e))
            raise RuntimeError("Could not connect to Redis") from e

    def set(
        self,
        key: str,
        value: Union[str, dict, list],
        ttl: int = 3600,
    ) -> None:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self.client.set(key, value, ex=ttl)
        except Exception as e:
            logger.error(f" Failed to cache key {key}: {e}")

    def get(self, key: str) -> Optional[str]:
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f" Failed to retrieve key {key}: {e}")
            return None

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f" Failed to delete cache key {key}: {e}")

    def exists(self, key: str) -> bool:
        try:
            return self.client.exists(key) == 1
        except Exception as e:
            logger.error(f" Redis exists check failed for {key}: {e}")
            return False

    def flush_all(self) -> None:
        try:
            self.client.flushall()
        except Exception as e:
            logger.error(" Failed to flush Redis DB: %s", e)


redis_client = RedisClient()