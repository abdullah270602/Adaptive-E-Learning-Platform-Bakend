import logging
import httpx
import os
import asyncio
from typing import List, Dict
from app.services.constants import HUGGINGFACE_API_URL
from app.services.models import get_next_api_key


logger = logging.getLogger(__name__)


def get_huggingface_headers():
    """ Get the headers for the Hugging Face API. """ 
    
    HUGGINGFACE_API_KEY = get_next_api_key("huggingface")
    return {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    

def preprocess_chunk(chunk: str, max_length: int = 512) -> str:
    """Truncate chunk to model token limits if needed"""
    # Rough token estimation (1 token ≈ 4 characters for English)
    estimated_tokens = len(chunk) // 4
    if estimated_tokens > max_length:
        # Truncate to approximate token limit, leaving room for special tokens
        char_limit = (max_length - 10) * 4
        chunk = chunk[:char_limit]
        
        # Try to end at a word boundary
        last_space = chunk.rfind(' ')
        if last_space > char_limit * 0.8:  # Only if we don't lose too much
            chunk = chunk[:last_space]
    
    return chunk

async def embed_single_chunk(client: httpx.AsyncClient, chunk: str, max_retries: int = 3) -> List[float]:
    """Embed a single chunk with retry logic and preprocessing"""
    processed_chunk = preprocess_chunk(chunk)
    headers = get_huggingface_headers()
    for attempt in range(max_retries):
        try:
            response = await client.post(
                HUGGINGFACE_API_URL,
                json={"inputs": processed_chunk},
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()

            # Hugging Face returns a list of vectors
            if isinstance(data, list) and all(isinstance(val, (int, float)) for val in data):
                return data
            else:
                print(f"Unexpected response format on attempt {attempt + 1}: {data}")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                await asyncio.sleep(wait_time)
            elif e.response.status_code >= 500:  # Server error
                wait_time = 1 * attempt
                print(f"Server error, waiting {wait_time}s before retry {attempt + 1}")
                await asyncio.sleep(wait_time)
            else:
                print(f"HTTP error on attempt {attempt + 1}: {e}")
                break
        except Exception as e:
            print(f"Embedding failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)

    return []

async def embed_texts(
    chunks: List[str],
    user_id: str,
    doc_id: str,
    doc_type: str,
    max_concurrent: int = 5
) -> List[Dict]:
    """
    Generate embeddings for chunks with rate limiting and error handling.
    Returns list of dicts containing embeddings and metadata.
    """
    if not chunks:
        print("No chunks provided")
        return []
    
    print(f"Generating embeddings for {len(chunks)} chunks...")
    
    # Rate limiting with semaphore
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def embed_with_semaphore(client: httpx.AsyncClient, chunk: str, index: int):
        async with semaphore:
            embedding = await embed_single_chunk(client, chunk)
            return index, embedding

    async with httpx.AsyncClient() as client:
        tasks = [embed_with_semaphore(client, chunk, i) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)

    embedded_docs = []
    failed_count = 0
    
    for index, emb in results:
        if emb:  # Only add successful embeddings
            embedded_docs.append({
                "embedding": emb,
                "metadata": {
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "chunk_index": index,
                    "chunk_text": chunks[index],
                    "chunk_length": len(chunks[index]),
                    "embedding_dim": len(emb)
                }
            })
        else:
            failed_count += 1
    
    success_rate = (len(embedded_docs) / len(chunks)) * 100 if chunks else 0
    print(f"Embedding complete: {len(embedded_docs)}/{len(chunks)} successful ({success_rate:.1f}%)")
    
    if failed_count > 0:
        print(f"⚠️  {failed_count} chunks failed to embed")
    
    return embedded_docs
    
    

# Utility function for single text embedding
async def embed_single_text(text: str) -> List[float]:
    """Generate embedding for a single text string"""
    try:
        async with httpx.AsyncClient() as client:
            return await embed_single_chunk(client, text)
    except Exception as e:
        print(f"Single text embedding failed: {e}")
        return []
