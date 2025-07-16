import re
import logging
from app.services.models import get_client_for_service
from app.services.prompts import DIAGRAM_GENERATION_PROMPT

logger = logging.getLogger(__name__)

def post_process_mermaid(diagram: str) -> str:
    """Cleans and standardizes Mermaid diagram code."""
    lines = [line.strip() for line in diagram.split("\n") if line.strip()]
    if not lines or lines[0] != "graph TD":
        lines.insert(0, "graph TD")

    processed_lines = ["graph TD"]
    for line in lines[1:]:
        line = re.sub(r"[^A-Za-z0-9_()\[\]\-\-> ]", "", line)
        line = re.sub(r'-->', ' --> ', line)
        processed_lines.append(f"    {line.strip()}")

    return "\n".join(processed_lines)

def extract_mermaid_diagrams(text: str) -> list[str]:
    """Extracts Mermaid code blocks from raw LLM response."""
    return re.findall(r'```mermaid\n(.*?)\n```', text, re.DOTALL)


async def generate_diagrams(content: str, title: str, chapter_name: str, section_name: str, learning_profile: str) -> list[str]:
    """
    Generates visual diagrams (Mermaid format) based on learning content and user profile.
    """
    prompt = DIAGRAM_GENERATION_PROMPT.format(
        book_name=title,
        content=content,
        chapter_name= chapter_name or "N/A",
        section_name=section_name or "N/A",
        learning_profile=learning_profile
    )

    try:
        client = get_client_for_service("groq")
        logger.info(f"[Diagrams] Generating diagrams for: {title}")
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct", # TODO set a model that is best for this kind of task
            messages=[
                {"role": "system", "content": "You are an expert at creating educational Mermaid flowcharts. Generate clear, meaningful diagrams that help users understand and remember concepts. Always return only Mermaid syntax with no additional text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )

        raw_content = response.choices[0].message.content
        diagrams = extract_mermaid_diagrams(raw_content)
        return [post_process_mermaid(d) for d in diagrams]

    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"[Diagrams] Generation failed: {e}")
        return []
