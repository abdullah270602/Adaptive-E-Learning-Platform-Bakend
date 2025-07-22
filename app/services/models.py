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
_api_key_cycles = {}
_api_key_locks = {}


def _init_api_key_cycle(service_prefix: str):
    """Initialize the cycle from env variables like PREFIX_API_KEY, PREFIX_API_KEY_2, etc."""
    
    prefix = f"{service_prefix}_API_KEY"
    keys = []

    for k, v in os.environ.items():
        if k.startswith(prefix) and v.strip():
            logger.info(f"Found API key for {service_prefix}: {k}")
            keys.append(v.strip())

    if not keys:
        logger.error(f"No API keys found for prefix: {prefix}")
        raise ValueError(f"No {service_prefix} API keys found in environment.")

    return cycle(keys)


def get_next_api_key(service: str):
    """Get next API key from the rotation for the specified service."""
    service_prefix = service.upper()
    
    if service_prefix not in _api_key_locks:
        _api_key_locks[service_prefix] = Lock()
    
    # Ensure thread-safe access to the cycle
    with _api_key_locks[service_prefix]:
        
        # Initialize the cycle if not already initialized
        if service_prefix not in _api_key_cycles:
            _api_key_cycles[service_prefix] = _init_api_key_cycle(service_prefix)
        return next(_api_key_cycles[service_prefix])


def get_client_for_service(service: str = "groq") -> OpenAI:
    try:
        config = SERVICE_CONFIG[service.lower()]
        base_url = config["base_url"]
        
        if config.get("use_key_rotation", False):
            api_key = get_next_api_key(service)
            logger.info(f"Using {service.upper()} API key: {api_key} (from cycle)")
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

    Args:
        model_id (str): The ID of the model to use.
        chat (list[str]): The chat history to use.
        Example :
            [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_message},
            ]
        
    Returns:
        str: The raw reply from the model.
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
