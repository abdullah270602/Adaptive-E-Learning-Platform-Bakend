import httpx
import os
from typing import List, Dict
import asyncio
from dotenv import load_dotenv

load_dotenv()


HUGGINGFACE_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
HF_TOKEN = os.getenv("HF_TOKEN")  # Make sure this is set in your .env



HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

async def embed_single_chunk(client: httpx.AsyncClient, chunk: str) -> List[float]:
    try:
        response = await client.post(
            HUGGINGFACE_API_URL,
            json={"inputs": chunk},
            headers=HEADERS,
            timeout=60
        )
        response.raise_for_status()

        data = response.json()

        # Hugging Face returns a list of vectors
        if isinstance(data, list) and all(isinstance(val, float) for val in data):
            return data
        else:
            print(f"Unexpected response format: {data}")
            return []

    except Exception as e:
        print(f"Embedding failed for chunk: {e}")
        return []

async def embed_texts(
    chunks: List[str],
    user_id: str,
    doc_id: str,
    doc_type: str
) -> List[Dict]:
    """Returns list of dicts containing embeddings and metadata."""
    async with httpx.AsyncClient() as client:
        tasks = [embed_single_chunk(client, chunk) for chunk in chunks]
        embeddings = await asyncio.gather(*tasks)

    embedded_docs = []
    for i, emb in enumerate(embeddings):
        if not emb:
            continue  # Skip if embedding failed
        embedded_docs.append({
            "embedding": emb,
            "metadata": {
                "user_id": user_id,
                "doc_id": doc_id,
                "doc_type": doc_type,
                "chunk_index": i
            }
        })
    return embedded_docs
