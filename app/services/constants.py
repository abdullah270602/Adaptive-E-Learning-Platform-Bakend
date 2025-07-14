LLAMA_3_70b = "llama-3.3-70b-versatile"
SYSTEM_ROLE = "system"
USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
DEFAULT_MODEL_ID = "d50a33ce-2462-4a5a-9aa7-efc2d1749745"

SERVICE_CONFIG = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env_var": "GROQ_API_KEY",
    },
     "huggingface": {
        "base_url": "https://router.huggingface.co/featherless-ai/v1",
        "api_key_env_var": "HF_TOKEN",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env_var": "DEEPSEEK_API_KEY",
    }
}