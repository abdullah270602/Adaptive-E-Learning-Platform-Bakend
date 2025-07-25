import logging
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from uuid import uuid4
import os

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

DEFAULT_VECTOR_SIZE = 384  # Assumes all-MiniLM embeddings
DEFAULT_COLLECTION_PREFIX = "user_docs_"


def empty_collection(user_id: str) -> dict:
    """
    Deletes all points from a user's collection.
    """
    try:
        collection_name = f"{DEFAULT_COLLECTION_PREFIX}{user_id}"

        if not client.collection_exists(collection_name):
            return {
                "status": "error",
                "message": f"Collection {collection_name} does not exist",
            }

        # Use Qdrant's Filter object with MatchAll
        client.delete_collection(collection_name=collection_name)

        return {
            "status": "success",
            "message": f"Collection {collection_name} has been emptied",
            "collection_name": collection_name,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(f"[Vector Storage] Failed to empty collection: {e}")
        return None


def ensure_collection_exists(
    user_id: str, vector_size: int = DEFAULT_VECTOR_SIZE
) -> str:
    """
    Ensure that a Qdrant collection exists for the given user.
    """
    # result = empty_collection(user_id)
    # logger.info(f"[Vector Storage] Emptying collection result: {result}")

    collection_name = f"{DEFAULT_COLLECTION_PREFIX}{user_id}"
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    return collection_name


def store_embeddings_to_qdrant(embedded_data: list[dict]) -> dict:
    """
    Stores embedded chunks in the appropriate Qdrant collection for the user.
    Expects `embedded_data` as a list of dicts with 'embedding' and 'metadata' keys.
    """
    if not embedded_data or not isinstance(embedded_data, list):
        raise ValueError("No embedded data provided for vector storage.")

    first_item = embedded_data[0]
    user_id = first_item["metadata"].get("user_id")
    embedding_dim = len(first_item["embedding"])

    collection_name = ensure_collection_exists(
        user_id=user_id, vector_size=embedding_dim
    )

    points = []
    for item in embedded_data:
        vector = item["embedding"]
        metadata = item["metadata"]

        # Explicitly extract only required fields from metadata
        payload = {
            "user_id": metadata.get("user_id"),
            "doc_id": metadata.get("doc_id"),
            "chunk_index": metadata.get("chunk_index"),
            "chunk_text": metadata.get("chunk_text"),
            "chunk_length": metadata.get(
                "chunk_length", len(metadata.get("chunk_text", ""))
            ),
            "embedding_dim": len(vector),
        }

        points.append(PointStruct(id=str(uuid4()), vector=vector, payload=payload))

    client.upsert(collection_name=collection_name, points=points)

    return {
        "collection_name": collection_name,
        "user_id": user_id,
        "total_chunks_stored": len(points),
        "embedding_dimension": embedding_dim,
        "status": "success",
    }
