from datetime import datetime, date
import decimal
import json
import redis
import os
import logging
from typing import Optional, Union
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(
        self,
        host=os.getenv("REDIS_HOST", "localhost"),
        port=os.getenv("REDIS_PORT", 6379),
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
        except redis.exceptions.ConnectionError as e:
            import traceback; traceback.print_exc();
            logger.critical(" Redis connection failed: %s", str(e))
            raise RuntimeError("Could not connect to Redis") from e

    def set(
        self,
        key: str,
        value: Union[str, dict, list],
        ttl: int = 3600,
    ) -> None:
        try:
            if not isinstance(value, str):
                value = json.dumps(value, default=self._json_serializer)
            self.client.set(key, value, ex=ttl)
            logger.info(f" Cached key {key} with TTL {ttl}")
        except Exception as e:
            logger.error(f" Failed to cache key {key}: {e}")

    def get(self, key: str) -> Optional[str]:
        try:
            
            value = self.client.get(key)
            logger.info(f" Retrieved key from cache {key}")
            return value
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
            logger.info(" Flushed all Redis DB")
        except Exception as e:
            logger.error(" Failed to flush Redis DB: %s", e)
            
    @staticmethod
    def _json_serializer(obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")


redis_client = RedisClient()
