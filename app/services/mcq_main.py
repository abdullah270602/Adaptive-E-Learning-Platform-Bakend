import os
from app.services.extraction import extract_and_preprocess_text
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts  # New import

async def process_mcq_document(
    tmp_path: str,
    filename: str,
    user_id: str,
    doc_id: str,
    doc_type: str
) -> dict:
    try:
        extension = os.path.splitext(filename)[1].lower()

        # Step 1: Extract text from document
        extracted_text = await extract_and_preprocess_text(tmp_path, extension)

        if not extracted_text or not extracted_text.strip():
            return {
                "extracted_text": None,
                "chunks": [],
                "Chunks_count": 0,
                "embeddings": [],
                "error": "No extractable text found. This PDF may be scanned or image-based. Consider OCR."
            }

        # Step 2: Chunk the text
        chunks = chunk_text(
            extracted_text,
            chunk_size=1500,
            chunk_overlap=300,
            max_chunks=2000
        )

        # Step 3: Embed the chunks
        embedded_data = await embed_texts(
            chunks=chunks,
            user_id=user_id,
            doc_id=doc_id,
            doc_type=doc_type
        )

        # Step 4: Return processed data
        return {
            "chunks": chunks,
            "Chunks_count": len(chunks),
            "embeddings": embedded_data
        }

    except Exception as e:
        raise RuntimeError(f"[MCQ Pipeline] Failed: {str(e)}")
