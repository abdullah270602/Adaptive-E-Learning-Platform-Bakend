import re
from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 300,
    max_chunks: int = 1000
) -> List[str]:
    """
    Splits input text into overlapping chunks with proper validations.
    """
    # Type checks
    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")
    if not isinstance(chunk_size, int) or not isinstance(chunk_overlap, int) or not isinstance(max_chunks, int):
        raise TypeError("chunk_size, chunk_overlap, and max_chunks must all be integers.")

    # Value checks
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and less than chunk_size.")
    if max_chunks <= 0:
        raise ValueError("max_chunks must be a positive integer.")

    # Content check
    if not text.strip():
        raise ValueError("Input text is empty or only whitespace.")

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    text_len = len(text)

    chunks = []
    start = 0
    count = 0

    while start < text_len and count < max_chunks:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - chunk_overlap
        count += 1

    if start < text_len:
        print(f"⚠️ Warning: Reached max_chunks limit ({max_chunks}). Some content may be left unprocessed.")

    return chunks
