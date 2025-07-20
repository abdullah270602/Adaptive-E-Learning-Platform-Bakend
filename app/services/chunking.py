import re
from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 300,
    max_chunks: int = 2000
) -> List[str]:
    """
    Splits input text into overlapping chunks with proper validations and smart boundary detection.
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

    # Improved text normalization - preserve sentence structure
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace but keep structure
    text_len = len(text)

    # If text is smaller than chunk_size, return as single chunk
    if text_len <= chunk_size:
        return [text]

    chunks = []
    start = 0
    count = 0

    while start < text_len and count < max_chunks:
        # Calculate ideal end position
        ideal_end = min(start + chunk_size, text_len)
        
        # If this would be the last chunk, take everything
        if ideal_end >= text_len:
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break
        
        # Find the best place to split (prioritize sentence boundaries)
        actual_end = _find_best_split_point(text, start, ideal_end, chunk_overlap)
        
        # Extract chunk
        chunk = text[start:actual_end].strip()
        
        if chunk:
            chunks.append(chunk)
        
        # Calculate next starting point with proper overlap
        # Move forward by (chunk_size - overlap), but ensure we don't go backwards
        next_start = max(start + 1, actual_end - chunk_overlap)
        
        # Adjust start to avoid splitting words if possible
        if next_start < text_len and text[next_start] != ' ':
            # Look for the next word boundary
            word_boundary = text.find(' ', next_start)
            if word_boundary != -1 and word_boundary - start < chunk_size + chunk_overlap:
                next_start = word_boundary + 1
        
        start = next_start
        count += 1

    if start < text_len:
        print(f"⚠️ Warning: Reached max_chunks limit ({max_chunks}). Some content may be left unprocessed.")

    return chunks


def _find_best_split_point(text: str, start: int, ideal_end: int, overlap: int) -> int:
    """
    Find the best place to split text, prioritizing sentence boundaries.
    """
    # Don't look too far back to maintain reasonable chunk sizes
    min_end = max(start + (ideal_end - start) // 2, ideal_end - overlap * 2)
    
    # Look for sentence endings (. ! ?) followed by space or end
    for i in range(ideal_end - 1, min_end - 1, -1):
        if i + 1 < len(text):
            if text[i] in '.!?' and (text[i + 1] == ' ' or i + 1 == len(text)):
                # Check if this looks like a real sentence ending
                if _is_sentence_boundary(text, i):
                    return i + 1
    
    # Look for other punctuation followed by space
    for i in range(ideal_end - 1, min_end - 1, -1):
        if i + 1 < len(text):
            if text[i] in ';:,' and text[i + 1] == ' ':
                return i + 1
    
    # Look for word boundaries (spaces)
    for i in range(ideal_end - 1, min_end - 1, -1):
        if text[i] == ' ':
            return i
    
    # If no good split point found, use the ideal end
    return ideal_end


def _is_sentence_boundary(text: str, pos: int) -> bool:
    """
    Check if a period/exclamation/question mark is likely a real sentence boundary.
    """
    if pos < 0 or pos >= len(text):
        return False
    
    char = text[pos]
    
    # Must be sentence-ending punctuation
    if char not in '.!?':
        return False
    
    # Check for common abbreviations that shouldn't end sentences
    if char == '.':
        # Look at the word before the period
        word_start = pos - 1
        while word_start >= 0 and text[word_start] not in ' \n\t':
            word_start -= 1
        word_start += 1
        
        word_before = text[word_start:pos].lower()
        
        # Common abbreviations that shouldn't split
        abbrevs = {'mr', 'mrs', 'dr', 'prof', 'vs', 'etc', 'inc', 'corp', 'ltd', 
                   'co', 'jr', 'sr', 'st', 'ave', 'blvd', 'dept', 'univ', 'gov',
                   'org', 'com', 'edu', 'net', 'www', 'http', 'https', 'ftp'}
        
        if word_before in abbrevs:
            return False
        
        # Single letter followed by period (like "A. Smith")
        if len(word_before) == 1 and word_before.isalpha():
            return False
    
    # Check what comes after
    if pos + 1 < len(text):
        next_char = text[pos + 1]
        # Should be followed by space and capital letter for strong sentence boundary
        if next_char == ' ' and pos + 2 < len(text):
            char_after_space = text[pos + 2]
            if char_after_space.isupper() or char_after_space in '"\'(':
                return True
        # End of text is also a sentence boundary
        elif pos + 1 == len(text):
            return True
    
    return False
