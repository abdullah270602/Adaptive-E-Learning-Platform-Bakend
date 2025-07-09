import logging
import os
from openai import OpenAI
from app.database.connection import PostgresConnection
from app.services.constants import SERVICE_CONFIG


logger = logging.getLogger(__name__)


def get_client_for_service(service: str = "groq") -> OpenAI:
    try:
        config = SERVICE_CONFIG[service.lower()]
        base_url = config["base_url"]
        api_key = os.getenv(config["api_key_env_var"])
        
        if not api_key:
            logger.critical(f"API key for service {service} not found in environment variables.")
            raise ValueError(f"API key for service {service} not found in environment variables.")
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        return client
    except KeyError as e:
        logger.error(f"Service configuration for '{service}' is missing: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error creating client for service '{service}': {e}", exc_info=True)
        raise