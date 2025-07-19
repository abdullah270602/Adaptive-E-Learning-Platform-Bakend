import logging
import os
from itertools import cycle
from threading import Lock
from openai import OpenAI
from app.cache.models import get_active_model_by_id_cached
from app.database.connection import PostgresConnection
from app.services.constants import SERVICE_CONFIG


logger = logging.getLogger(__name__)

# State for rotation
_groq_key_cycle = None
_groq_key_lock = Lock()

def _init_groq_key_cycle_from_env():
    """Initialize the cycle from env variables like GROQ_API_KEY, GROQ_API_KEY_2, etc."""
    
    prefix = "GROQ_API_KEY"
    keys = []

    for k, v in os.environ.items():
        if k.startswith(prefix) and v.strip():
            logger.info(f"Found GROQ API key in environment variable: {k}")
            keys.append(v.strip())

    if not keys:
        raise ValueError("No GROQ API keys found in environment.")

    return cycle(keys)


def get_client_for_service(service: str = "groq") -> OpenAI:
    try:
        config = SERVICE_CONFIG[service.lower()]
        base_url = config["base_url"]
        
        if service.lower() == "groq":
            global _groq_key_cycle
            with _groq_key_lock:
                if not _groq_key_cycle:
                    _groq_key_cycle = _init_groq_key_cycle_from_env()
                api_key = next(_groq_key_cycle)
                logger.info(f"Using GROQ API key: {api_key} (from cycle)")
                
        else:
            api_key = os.getenv(config["api_key_env_var"])

        if not api_key:
            logger.critical(
                f"API key for service {service} not found in environment variables."
            )
            raise ValueError(
                f"API key for service {service} not found in environment variables."
            )

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        return client
    except KeyError as e:
        logger.error(
            f"Service configuration for '{service}' is missing: {e}", exc_info=True
        )
        raise
    except Exception as e:
        logger.error(
            f"Error creating client for service '{service}': {e}", exc_info=True
        )
        raise


def get_reply_from_model(model_id: str, chat: list[str]) -> str:
    """
    Main entrypoint to retrieve a reply from the specified model.
    """
    try:
        with PostgresConnection() as conn:
            model_data = get_active_model_by_id_cached(conn, model_id)
            service = model_data["service"]
            model_name = model_data["model_name"]
            logger.info(
                f"Retrieved model info: model_name={model_name}, service={service}"
            )
    except Exception as e:
        logger.error(
            f"Database error or model lookup failure for model_id {model_id}: {e}",
            exc_info=True,
        )
        raise

    try:
        # Dynamically get the client based on service
        client = get_client_for_service(service)
    except Exception as e:
        logger.error(
            f"Failed to create client for service {service}: {e}", exc_info=True
        )
        raise

    try:

        response = client.chat.completions.create(model=model_name, messages=chat)
        # Validate response structure before accessing
        if not response.choices or not response.choices[0].message:
            raise ValueError("Incomplete response received from LLM service.")

        reply = response.choices[0].message.content
        return reply
    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(
            f"Error during chat completion call for model {model_name}: {e}",
            exc_info=True,
        )
        raise
