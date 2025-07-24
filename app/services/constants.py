SYSTEM_ROLE = "system"
USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"

LLAMA_3_70b = "llama-3.3-70b-versatile"
QWEN_CODER_32b = "Qwen/Qwen2.5-Coder-32B-Instruct"
DEFAULT_MODEL_ID = "d50a33ce-2462-4a5a-9aa7-efc2d1749745" # LLAMA_3_70b
DEEPSEEK_CHAT_ID = "a1b6e28b-6c75-4695-be78-ce8fa3c11c06" # DeepSeek Chat
KIMI_K2_INSTRUCT = "moonshotai/kimi-k2-instruct"
KIMI_K2_INSTRUCT_ID ="0068ad8d-ff21-4633-8c8e-6bb0282e0d82" # Kimi-K2-Instruct


WINDOWS_SOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.com"
LINUX_SOFFICE_PATH = "/usr/lib/libreoffice/program/soffice.bin"

HUGGINGFACE_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"


SERVICE_CONFIG = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env_var": "GROQ_API_KEY",
        "use_key_rotation": True
    },
     "huggingface_featherless": {
        "base_url": "https://router.huggingface.co/featherless-ai/v1",
        "api_key_env_var": "HUGGINGFACE_API_KEY",
    },
     "huggingface_hyberbolic": {
        "base_url": "https://router.huggingface.co/hyperbolic/v1",
        "api_key_env_var": "HUGGINGFACE_API_KEY",
        "use_key_rotation": True
    },
     "huggingface": {
        "base_url": "https://router.huggingface.co/v1",
        "api_key_env_var": "HUGGINGFACE_API_KEY",
        "use_key_rotation": True
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env_var": "DEEPSEEK_API_KEY",
    }
}
