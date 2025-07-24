from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Filter, SearchRequest
from typing import List, Dict
import logging
import os
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Enhanced client initialization with better configuration
client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY,
    timeout=30.0,  # Add timeout for better error handling
    # Connection pooling for better performance
    prefer_grpc=True,  # Use gRPC for better performance
    grpc_options={
        "grpc.keepalive_time_ms": 30000,
        "grpc.keepalive_timeout_ms": 5000,
        "grpc.http2.max_pings_without_data": 0,
        "grpc.http2.min_time_between_pings_ms": 10000,
        "grpc.http2.min_ping_interval_without_data_ms": 300000
    }
)

DEFAULT_COLLECTION_PREFIX = "user_docs_"

# Cache for collection existence checks to improve performance
@lru_cache(maxsize=1000)
def _cached_collection_exists(collection_name: str) -> bool:
    """Cached collection existence check to avoid repeated API calls."""
    try:
        return client.collection_exists(collection_name)
    except Exception as e:
        logger.error(f"Error checking collection existence for {collection_name}: {e}")
        return False

def _clear_collection_cache():
    """Clear the collection existence cache."""
    _cached_collection_exists.cache_clear()

async def _perform_search_with_retry(collection_name: str, query_vector: List[float], 
                                   limit: int, with_payload: bool) -> List:
    """Perform search with retry logic for better reliability."""
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            return client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=with_payload
            )
        except (UnexpectedResponse, ConnectionError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt)  # Exponential backoff
            logger.warning(f"Search attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise e

def _validate_and_sanitize_inputs(embedded_query: List[float], user_id: str, top_k: int) -> tuple:
    """Validate and sanitize input parameters."""
    # Validate embedded_query
    if not embedded_query:
        raise ValueError("embedded_query cannot be empty")
    if not isinstance(embedded_query, list):
        raise ValueError("embedded_query must be a list")
    if not all(isinstance(x, (int, float)) for x in embedded_query):
        raise ValueError("embedded_query must contain only numbers")
    
    # Validate and sanitize user_id
    if not user_id:
        raise ValueError("user_id cannot be empty")
    user_id = str(user_id).strip()
    if not user_id:
        raise ValueError("user_id cannot be empty after stripping")
    
    # Validate and cap top_k
    if not isinstance(top_k, int) or top_k < 1:
        logger.warning(f"Invalid top_k value {top_k}, setting to 10")
        top_k = 10
    
    # Cap top_k for performance (max 100)
    top_k = min(top_k, 100)
    
    return embedded_query, user_id, top_k

def _process_and_validate_results(search_results: List, user_id: str) -> List[Dict]:
    """Process and validate search results with better error handling."""
    if not search_results:
        return []
    
    chunks = []
    for i, result in enumerate(search_results):
        try:
            # Validate result structure
            if not hasattr(result, 'payload') or not hasattr(result, 'score'):
                logger.warning(f"Invalid result structure at index {i}, skipping")
                continue
            
            payload = result.payload or {}
            
            # Extract and validate text content
            chunk_text = payload.get("chunk_text", "")
            if not isinstance(chunk_text, str):
                chunk_text = str(chunk_text) if chunk_text is not None else ""
            chunk_text = chunk_text.strip()
            
            # Validate score
            score = result.score
            if score is None:
                logger.warning(f"Missing score for result {i}, setting to 0.0")
                score = 0.0
            elif not isinstance(score, (int, float)):
                logger.warning(f"Invalid score type for result {i}, converting to float")
                try:
                    score = float(score)
                except (ValueError, TypeError):
                    score = 0.0
            
            # Extract metadata with safe type conversion
            doc_id = payload.get("doc_id")
            if doc_id is not None and not isinstance(doc_id, str):
                doc_id = str(doc_id)
            
            chunk_index = payload.get("chunk_index")
            if chunk_index is not None and not isinstance(chunk_index, int):
                try:
                    chunk_index = int(chunk_index)
                except (ValueError, TypeError):
                    chunk_index = None
            
            chunk_data = {
                "text": chunk_text,
                "score": float(score),
                "doc_id": doc_id,
                "chunk_index": chunk_index,
            }
            
            # Only add chunks with actual content
            if chunk_text:
                chunks.append(chunk_data)
            else:
                logger.debug(f"Skipping empty chunk at index {i}")
                
        except Exception as e:
            logger.warning(f"Error processing result {i}: {e}")
            continue
    
    logger.info(f"Processed {len(chunks)} valid chunks out of {len(search_results)} results for user {user_id}")
    return chunks

async def search_similar_chunks(
    embedded_query: List[float],
    user_id: str,
    top_k: int = 3
) -> List[Dict]:
    """
    Searches a user-specific Qdrant collection using a query embedding.
    Returns top-k matching chunks with associated metadata.

    Args:
        embedded_query (List[float]): The embedded vector of the expanded query.
        user_id (str): The user's ID (used for collection lookup).
        top_k (int): Number of results to return.

    Returns:
        List[Dict]: List of matched chunks with text and metadata.
    """
    try:
        # Validate and sanitize inputs
        embedded_query, user_id, top_k = _validate_and_sanitize_inputs(embedded_query, user_id, top_k)
        
        collection_name = f"{DEFAULT_COLLECTION_PREFIX}{user_id}"
        
        # Check collection existence with caching
        if not _cached_collection_exists(collection_name):
            logger.warning(f"Collection {collection_name} does not exist for user.")
            return []
        
        # Perform search with retry logic
        search_results = await _perform_search_with_retry(
            collection_name=collection_name,
            query_vector=embedded_query,
            limit=top_k,
            with_payload=True
        )
        
        # Process and validate results
        chunks = _process_and_validate_results(search_results, user_id)
        
        return chunks

    except ValueError as e:
        logger.error(f"Input validation error: {e}")
        return []
        
    except UnexpectedResponse as e:
        logger.error(f"Qdrant error: {str(e)}")
        # Clear cache in case collection was deleted
        _clear_collection_cache()
        return []

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Connection/timeout error: {e}")
        return []
        
    except Exception as ex:
        logger.exception("Unexpected error during similarity search")
        return []

# Utility functions for monitoring and maintenance

def get_client_health() -> bool:
    """Check if the Qdrant client is healthy."""
    try:
        collections = client.get_collections()
        return True
    except Exception as e:
        logger.error(f"Client health check failed: {e}")
        return False

def get_collection_stats(user_id: str) -> Dict:
    """Get basic statistics for a user's collection."""
    collection_name = f"{DEFAULT_COLLECTION_PREFIX}{user_id}"
    
    try:
        if not _cached_collection_exists(collection_name):
            return {"exists": False}
        
        collection_info = client.get_collection(collection_name)
        return {
            "exists": True,
            "points_count": collection_info.points_count,
            "vectors_count": getattr(collection_info, 'vectors_count', None),
            "indexed_vectors_count": getattr(collection_info, 'indexed_vectors_count', None),
        }
    except Exception as e:
        logger.error(f"Error getting collection stats for {collection_name}: {e}")
        return {"exists": False, "error": str(e)}

def clear_caches():
    """Clear all internal caches."""
    _clear_collection_cache()
    logger.info("Cleared all caches")