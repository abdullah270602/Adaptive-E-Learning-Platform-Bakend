import os
from app.services.extraction import extract_text_from_file

async def process_mcq_document(tmp_path: str, filename: str) -> dict:
    try:
        extension = os.path.splitext(filename)[1].lower()

        # Extract text
        extracted_text = await extract_text_from_file(tmp_path, extension)

        # Return just the extracted text for now
        return {
            "extracted_text": extracted_text
        }

    except Exception as e:
        raise RuntimeError(f"[MCQ Pipeline] Failed: {str(e)}")
