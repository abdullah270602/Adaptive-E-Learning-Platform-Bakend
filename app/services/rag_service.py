from typing import List, Dict, Optional
import logging
from app.services.vector_search import search_similar_chunks
from app.services.embeddings import embed_single_text
from app.database.library_queries import get_documents_metadata_by_ids
from app.database.connection import PostgresConnection
from app.services.models import get_client_for_service
from app.services.constants import LLAMA_3_70b
from app.services.prompts import RAG_SYSTEM_PROMPT, ASK_MY_LIBRARY_USER_PROMPT
import json

logger = logging.getLogger(__name__)


async def multi_strategy_search(
    query: str, user_id: str, max_chunks: int
) -> List[Dict]:
    """
    Use multiple search strategies to find diverse results across different documents
    """
    try:
        all_chunks = []
        chunk_ids_seen = set()

        # Full query search
        logger.info("Strategy 1: Full query search")
        full_query_embedding = await embed_single_text(query)
        if full_query_embedding:
            chunks1 = await search_similar_chunks(
                embedded_query=full_query_embedding, user_id=user_id, top_k=max_chunks
            )
            for chunk in chunks1:
                chunk_id = f"{chunk.get('doc_id')}_{chunk.get('chunk_index')}"
                if chunk_id not in chunk_ids_seen:
                    chunk_ids_seen.add(chunk_id)
                    all_chunks.append(chunk)

        # Split query by "and" and search separately
        if " and " in query.lower():
            logger.info("Strategy 2: Split query by 'and'")
            sub_queries = [q.strip() for q in query.lower().split(" and ") if q.strip()]

            for i, sub_query in enumerate(sub_queries[:2]):  # Limit to 2 sub-queries
                logger.info(f"Sub-query {i+1}: '{sub_query}'")
                sub_embedding = await embed_single_text(sub_query)
                if sub_embedding:
                    sub_chunks = await search_similar_chunks(
                        embedded_query=sub_embedding,
                        user_id=user_id,
                        top_k=max_chunks // 2,  # Fewer per sub-query
                    )
                    for chunk in sub_chunks:
                        chunk_id = f"{chunk.get('doc_id')}_{chunk.get('chunk_index')}"
                        if chunk_id not in chunk_ids_seen:
                            chunk_ids_seen.add(chunk_id)
                            # Add sub-query info for debugging
                            chunk["sub_query"] = sub_query
                            all_chunks.append(chunk)

        # Extract key terms and search
        key_terms = extract_key_terms(query)
        if key_terms:
            logger.info(f"Strategy 3: Key terms search: {key_terms}")
            for term in key_terms[:3]:  # Top 3 key terms
                term_embedding = await embed_single_text(term)
                if term_embedding:
                    term_chunks = await search_similar_chunks(
                        embedded_query=term_embedding,
                        user_id=user_id,
                        top_k=5,  # Fewer per term
                    )
                    for chunk in term_chunks:
                        chunk_id = f"{chunk.get('doc_id')}_{chunk.get('chunk_index')}"
                        if chunk_id not in chunk_ids_seen:
                            chunk_ids_seen.add(chunk_id)
                            chunk["key_term"] = term
                            all_chunks.append(chunk)

        # Sort by score and limit total results
        all_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
        limited_chunks = all_chunks[: max_chunks * 2]  # Allow more for diversity

        logger.info(
            f"Multi-strategy found {len(limited_chunks)} unique chunks from {len(set(c.get('doc_id') for c in limited_chunks))} documents"
        )
        return limited_chunks

    except Exception as e:
        logger.error(f"Multi-strategy search failed: {e}")
        # Fallback to simple search
        query_embedding = await embed_single_text(query)
        if query_embedding:
            return await search_similar_chunks(
                embedded_query=query_embedding, user_id=user_id, top_k=max_chunks
            )
        return []


def extract_key_terms(query: str) -> List[str]:
    """
    Extract key terms from a query for diversified search
    """
    # Simple key term extraction
    import re

    # Remove common words
    stop_words = {
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
    }

    # Split by common separators
    terms = re.split(r"[,\s\-_]+", query.lower())

    # Filter out stop words and short terms
    key_terms = [
        term.strip()
        for term in terms
        if term.strip() and len(term.strip()) > 2 and term.strip() not in stop_words
    ]

    return key_terms[:5]  # Return top 5 key terms


async def perform_library_search(
    query: str,
    user_id: str,
    max_chunks: int = 10,
    document_types: Optional[List[str]] = None,
    min_score: float = 0.7,
) -> Dict:
    """
    Perform RAG search across user's library
    """
    try:
        logger.info(f"Starting library search for user {user_id}: '{query}'")

        all_chunks = await multi_strategy_search(query, user_id, max_chunks)

        logger.info(f"Multi-strategy search found {len(all_chunks)} chunks")
        if all_chunks:
            scores = [chunk.get("score", 0) for chunk in all_chunks]
            logger.info(
                f"Score range: min={min(scores):.3f}, max={max(scores):.3f}, avg={sum(scores)/len(scores):.3f}"
            )

        if min_score > 0:
            before_filter = len(all_chunks)
            similar_chunks = [
                chunk for chunk in all_chunks if chunk.get("score", 0) >= min_score
            ]
            logger.info(
                f"Score filter (>={min_score}): {before_filter} -> {len(similar_chunks)} chunks"
            )
        else:
            similar_chunks = all_chunks

        if not similar_chunks:
            return {
                "answer": "I couldn't find any relevant information in your library for this query. Try using different keywords or check if you have documents uploaded.",
                "sources": [],
                "references": [],
            }
        
        # TODO FIlter by doc if needed in future
        similar_chunks = ensure_document_diversity(similar_chunks, max_per_doc=4)

        if document_types:
            similar_chunks = filter_chunks_by_type(similar_chunks, document_types)

        if not similar_chunks:
            return {
                "answer": f"I found some documents but none match the requested document types: {', '.join(document_types)}.",
                "sources": [],
                "references": [],
            }

        doc_ids = list(
            set(chunk["doc_id"] for chunk in similar_chunks if chunk["doc_id"])
        )

        logger.info(f"Found {len(similar_chunks)} chunks with doc_ids: {doc_ids}")
        for i, chunk in enumerate(similar_chunks[:3]):  # Log first 3 chunks
            logger.info(
                f"Chunk {i}: doc_id='{chunk.get('doc_id')}', text_length={len(chunk.get('text', ''))}, score={chunk.get('score')}"
            )

        with PostgresConnection() as conn:
            documents_metadata = get_documents_metadata_by_ids(conn, doc_ids, user_id)

        logger.info(
            f"Retrieved metadata for {len(documents_metadata)} documents: {list(documents_metadata.keys())}"
        )

        answer = await generate_rag_answer(query, similar_chunks, documents_metadata)

        # Format response
        return format_search_response(answer, similar_chunks, documents_metadata)

    except Exception as e:
        logger.error(f"RAG search failed: {str(e)}")
        return {
            "answer": "I encountered an error while searching your library. Please try again or contact support if the issue persists.",
            "sources": [],
            "references": [],
        }


def filter_chunks_by_type(chunks: List[Dict], document_types: List[str]) -> List[Dict]:
    """Filter chunks by document type based on metadata"""
    
    return chunks


def ensure_document_diversity(chunks: List[Dict], max_per_doc: int = 3) -> List[Dict]:
    """
    Ensure we don't get too many chunks from the same document
    """
    doc_chunk_count = {}
    diverse_chunks = []

    for chunk in chunks:
        doc_id = chunk.get("doc_id")
        if not doc_id:
            continue

        # Count chunks per document
        if doc_id not in doc_chunk_count:
            doc_chunk_count[doc_id] = 0

        # Only add if we haven't hit the limit for this document
        if doc_chunk_count[doc_id] < max_per_doc:
            diverse_chunks.append(chunk)
            doc_chunk_count[doc_id] += 1

    logger.info(
        f"Document diversity: {len(diverse_chunks)} chunks from {len(doc_chunk_count)} documents"
    )
    for doc_id, count in doc_chunk_count.items():
        logger.info(f"  Document {doc_id[:8]}...: {count} chunks")

    return diverse_chunks


async def generate_rag_answer(
    query: str, chunks: List[Dict], documents_metadata: Dict
) -> str:
    """Generate AI answer using retrieved chunks"""
    try:
        # Prepare context from chunks
        context_parts = []
        used_docs = set()

        for i, chunk in enumerate(chunks[:5]):  # Use top 5 chunks
            doc_id = chunk.get("doc_id")
            if not doc_id:
                continue

            doc_info = documents_metadata.get(doc_id, {})
            doc_title = doc_info.get("title", "Unknown Document")

            # Add document title only once
            if doc_id not in used_docs:
                context_parts.append(f"\n--- From: {doc_title} ---")
                used_docs.add(doc_id)

            # Clean and add chunk text
            chunk_text = chunk.get("text", "").strip()
            if chunk_text:
                context_parts.append(f"{chunk_text}")

        if not context_parts:
            return "I found relevant documents but couldn't extract readable content. Please try rephrasing your question."

        context = "\n".join(context_parts)

        # Use prompts from prompts.py for clean organization
        prompt = ASK_MY_LIBRARY_USER_PROMPT.format(query=query, context=context)

        client = get_client_for_service()
        response = client.chat.completions.create(
            model=LLAMA_3_70b,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=250,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Failed to generate RAG answer: {str(e)}")
        return "I found relevant information but couldn't generate a proper response. Please try rephrasing your question."


def format_search_response(
    answer: str, chunks: List[Dict], documents_metadata: Dict
) -> Dict:
    """Format the final search response"""

    unique_docs = {}
    for chunk in chunks:
        doc_id = chunk.get("doc_id")
        if doc_id and doc_id not in unique_docs:
            doc_info = documents_metadata.get(doc_id, {})
            if doc_info:  # Only include docs we have metadata for
                unique_docs[doc_id] = doc_info

    # Create sources list (just titles)
    sources = []
    for doc_info in unique_docs.values():
        title = doc_info.get("title") or doc_info.get(
            "original_filename", "Unknown Document"
        )
        sources.append(title)

    # Create references list, atm just titles
    references = []
    for doc_id, doc_info in unique_docs.items():
        title = doc_info.get("title") or doc_info.get(
            "original_filename", "Unknown Document"
        )
        doc_type = doc_info.get("document_type", "document")

        references.append(
            {
                "id": doc_id,
                "title": title,
                "topic": extract_topic_from_title(title),
                "type": doc_type.title(),
            }
        )

    return {
        "answer": answer,
        "sources": sources[:5],  # Limit to top 5 sources
        "references": references[:5],
    }


def extract_topic_from_title(title: str) -> str:
    """Extract a topic from document title"""
    if not title:
        return "General"

    cleaned = (
        title.replace("Chapter", "")
        .replace("Section", "")
        .replace(".pdf", "")
        .replace(".pptx", "")
        .replace(".docx", "")
        .strip()
    )

    # Take first few meaningful words as topic
    words = [word for word in cleaned.split()[:3] if len(word) > 2]
    return " ".join(words) if words else "General Topic"
