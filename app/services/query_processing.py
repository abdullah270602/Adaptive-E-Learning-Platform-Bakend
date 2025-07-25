# app/services/query_expansion.py

from app.services.prompts import EXPANSION_SYSTEM_PROMPT
from app.services.embeddings import embed_single_text  # Your existing embedding logic
from app.services.vector_search import search_similar_chunks  # You already have this
from app.services.models import get_reply_from_model  
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def expand_user_query_and_search(
    user_query: str,
    user_id: str,
    model_id: str,
    top_k: int = 5
) -> Optional[list[dict]]:
    """
    Expands the user query using an LLM and performs semantic search to retrieve top relevant chunks.

    Args:
        user_query (str): Original user query
        user_id (str): ID of the user making the request
        model_id (str): ID of the model to use for query expansion
        top_k (int): Number of chunks to retrieve

    Returns:
        List of relevant chunks or None
    """

    try:
        # Build the message payload for the model
        chat = [
            {"role": "system", "content": EXPANSION_SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ]

        # Step 1: Query Expansion
        expanded_query = get_reply_from_model(model_id=model_id, chat=chat)
        logger.info(f"Expanded Query: {expanded_query}")

        

        # Step 2: Embed Expanded Query
        embedded_query = await embed_single_text(expanded_query)

        if not embedded_query:
            raise ValueError("Failed to generate embedding for expanded query")

        # Step 3: Search relevant chunks from vector DB
        search_results = await search_similar_chunks(
            embedded_query=embedded_query,
            user_id=user_id,
            top_k=top_k
        )

        return search_results

    except Exception as e:
        logger.error(f"Error in expand_user_query_and_search: {e}", exc_info=True)
        return None
