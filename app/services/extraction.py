import os
import fitz  # PyMuPDF

async def extract_text_from_file(file_path: str, extension: str) -> str:
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract PDF: {str(e)}")
    finally:
        if 'doc' in locals():
            doc.close()
