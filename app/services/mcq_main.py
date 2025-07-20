import os
from app.services.extraction import extract_text_from_file
from app.services.chunking import chunk_text  

async def process_mcq_document(tmp_path: str, filename: str) -> dict:
    try:
        extension = os.path.splitext(filename)[1].lower()

        # Step 1: Extract text from the uploaded document
        extracted_text = await extract_text_from_file(tmp_path, extension)

        if not extracted_text:
            return {"error": "No text was extracted from the document."}

        # Step 2: Chunk the extracted text (using recommended size for all-MiniLM model)
        chunks = chunk_text(
            extracted_text,
            chunk_size=1500,
            chunk_overlap=300,
            max_chunks=1000
        )

        # Step 3: Return both original text and chunks
        return {
            "extracted_text": extracted_text,
            "chunks": chunks,
            "Chunks_count": len(chunks)
        }

    except Exception as e:
        raise RuntimeError(f"[MCQ Pipeline] Failed: {str(e)}")
