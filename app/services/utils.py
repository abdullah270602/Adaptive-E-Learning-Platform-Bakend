import os
import re
from openai import OpenAI


def extract_chapter_number(title: str) -> str:
    """Extracts the chapter number from a given title string."""
    match = re.search(r"Chapter\s+(\d+)", title, re.IGNORECASE)
    return match.group(1) if match else "N/A"

def get_openai_client():
    """ Initialize and return the OpenAI client with Groq configuration. """
    return OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url=os.getenv("GROQ_BASE_URL")
    )


