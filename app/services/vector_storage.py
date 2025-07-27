from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, PayloadSchemaType
from uuid import uuid4
import os
import logging

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

DEFAULT_VECTOR_SIZE = 384
DEFAULT_COLLECTION_PREFIX = "user_docs_"


def empty_collection(user_id: str) -> dict:
    try:
        collection_name = f"{DEFAULT_COLLECTION_PREFIX}{user_id}"

        if not client.collection_exists(collection_name):
            return {"status": "error", "message": f"Collection {collection_name} does not exist"}

        client.delete_collection(collection_name=collection_name)

        return {"status": "success", "message": f"Collection {collection_name} has been deleted", "collection_name": collection_name}
    except Exception as e:
        logger.exception("[Vector Storage] Failed to empty collection")
        return {"status": "error", "message": str(e)}


def ensure_collection_exists(user_id: str, vector_size: int = DEFAULT_VECTOR_SIZE) -> str:
    collection_name = f"{DEFAULT_COLLECTION_PREFIX}{user_id}"

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"[Vector Storage] Created new collection: {collection_name}")

    # ✅ Always try to create the index (safe if it already exists)
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info(f"[Vector Storage] Ensured doc_id index on {collection_name}")
    except Exception as e:
        logger.warning(f"[Vector Storage] Index may already exist on {collection_name}: {e}")

    return collection_name


def store_embeddings_to_qdrant(embedded_data: list[dict]) -> dict:
    if not embedded_data or not isinstance(embedded_data, list):
        raise ValueError("No embedded data provided for vector storage.")

    first_item = embedded_data[0]
    user_id = first_item["metadata"].get("user_id")
    embedding_dim = len(first_item["embedding"])

    collection_name = ensure_collection_exists(user_id, vector_size=embedding_dim)

    points = []
    for item in embedded_data:
        vector = item["embedding"]
        metadata = item["metadata"]

        payload = {
            "user_id": metadata.get("user_id"),
            "doc_id": metadata.get("doc_id"),
            "chunk_index": metadata.get("chunk_index"),
            "chunk_text": metadata.get("chunk_text"),
            "chunk_length": metadata.get("chunk_length", len(metadata.get("chunk_text", ""))),
        }

        points.append(PointStruct(id=str(uuid4()), vector=vector, payload=payload))

    try:
        client.upsert(collection_name=collection_name, points=points)
        return {
            "collection_name": collection_name,
            "user_id": user_id,
            "total_chunks_stored": len(points),
            "embedding_dimension": embedding_dim,
            "status": "success",
        }
    except Exception as e:
        logger.exception("[Vector Storage] Failed to upsert points")
        return {"status": "error", "message": str(e)}


def create_doc_id_index_for_existing_collections():
    try:
        collections = client.get_collections()
        for collection in collections.collections:
            collection_name = collection.name
            if not collection_name.startswith(DEFAULT_COLLECTION_PREFIX):
                continue
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name="doc_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                logger.info(f"Created doc_id index for: {collection_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Index already exists for: {collection_name}")
                else:
                    logger.error(f"Error creating index on {collection_name}: {e}")
    except Exception as e:
        logger.error(f"Failed to create indexes for existing collections: {e}")
