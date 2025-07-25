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

async def perform_library_search(
    query: str,
    user_id: str,
    max_chunks: int = 10,
    document_types: Optional[List[str]] = None,
    min_score: float = 0.7
) -> Dict:
    """
    Perform RAG search across user's library
    """
    try:
        # Step 1: Embed the query
        logger.info(f"Starting library search for user {user_id}: '{query}'")
        
        query_embedding = await embed_single_text(query)
        if not query_embedding:
            raise ValueError("Failed to generate query embedding")
        
        # Step 2: Search similar chunks
        similar_chunks = await search_similar_chunks(
            embedded_query=query_embedding,
            user_id=user_id,
            top_k=max_chunks
        )
        
        # Debug: Log chunks before filtering
        logger.info(f"Vector search found {len(similar_chunks)} chunks")
        if similar_chunks:
            scores = [chunk.get("score", 0) for chunk in similar_chunks]
            logger.info(f"Score range: min={min(scores):.3f}, max={max(scores):.3f}, avg={sum(scores)/len(scores):.3f}")
        
        # Filter by score if needed
        if min_score > 0:
            before_filter = len(similar_chunks)
            similar_chunks = [chunk for chunk in similar_chunks if chunk.get("score", 0) >= min_score]
            logger.info(f"Score filter (>={min_score}): {before_filter} -> {len(similar_chunks)} chunks")
        
        if not similar_chunks:
            return {
                "answer": "I couldn't find any relevant information in your library for this query. Try using different keywords or check if you have documents uploaded.",
                "sources": [],
                "references": []
            }
        
        # Step 3: Filter by document types if specified
        if document_types:
            similar_chunks = filter_chunks_by_type(similar_chunks, document_types)
        
        if not similar_chunks:
            return {
                "answer": f"I found some documents but none match the requested document types: {', '.join(document_types)}.",
                "sources": [],
                "references": []
            }
        
        # Step 4: Get document metadata using your efficient caching
        doc_ids = list(set(chunk["doc_id"] for chunk in similar_chunks if chunk["doc_id"]))
        
        # Debug logging
        logger.info(f"Found {len(similar_chunks)} chunks with doc_ids: {doc_ids}")
        for i, chunk in enumerate(similar_chunks[:3]):  # Log first 3 chunks
            logger.info(f"Chunk {i}: doc_id='{chunk.get('doc_id')}', text_length={len(chunk.get('text', ''))}, score={chunk.get('score')}")
        
        with PostgresConnection() as conn:
            documents_metadata = get_documents_metadata_by_ids(conn, doc_ids, user_id)
        
        logger.info(f"Retrieved metadata for {len(documents_metadata)} documents: {list(documents_metadata.keys())}")
        
        # Step 5: Generate AI response
        answer = await generate_rag_answer(query, similar_chunks, documents_metadata)
        
        # Step 6: Format response
        return format_search_response(answer, similar_chunks, documents_metadata)
        
    except Exception as e:
        logger.error(f"RAG search failed: {str(e)}")
        return {
            "answer": "I encountered an error while searching your library. Please try again or contact support if the issue persists.",
            "sources": [],
            "references": []
        }

def filter_chunks_by_type(chunks: List[Dict], document_types: List[str]) -> List[Dict]:
    """Filter chunks by document type based on metadata"""
    # This would need document type info in chunk metadata
    # For now, return all chunks - we'll filter at document level
    return chunks

async def generate_rag_answer(query: str, chunks: List[Dict], documents_metadata: Dict) -> str:
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
            chunk_text = chunk.get('text', '').strip()
            if chunk_text:
                context_parts.append(f"{chunk_text}")
        
        if not context_parts:
            return "I found relevant documents but couldn't extract readable content. Please try rephrasing your question."
        
        context = "\n".join(context_parts)
        
        # Use prompts from prompts.py for clean organization
        prompt = ASK_MY_LIBRARY_USER_PROMPT.format(
            query=query,
            context=context
        )

        client = get_client_for_service()
        response = client.chat.completions.create(
            model=LLAMA_3_70b,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Lower temperature for more focused responses
            max_tokens=200    # Much lower token limit for concise answers
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate RAG answer: {str(e)}")
        return "I found relevant information but couldn't generate a proper response. Please try rephrasing your question."

def format_search_response(answer: str, chunks: List[Dict], documents_metadata: Dict) -> Dict:
    """Format the final search response"""
    # Get unique documents
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
        title = doc_info.get("title") or doc_info.get("original_filename", "Unknown Document")
        sources.append(title)
    
    # Create references list
    references = []
    for doc_id, doc_info in unique_docs.items():
        title = doc_info.get("title") or doc_info.get("original_filename", "Unknown Document")
        doc_type = doc_info.get("document_type", "document")
        
        references.append({
            "id": doc_id,
            "title": title,
            "topic": extract_topic_from_title(title),
            "type": doc_type.title()
        })
    
    return {
        "answer": answer,
        "sources": sources[:5],  # Limit to top 5 sources
        "references": references[:5]
    }

def extract_topic_from_title(title: str) -> str:
    """Extract a topic from document title"""
    if not title:
        return "General"
    
    # Remove common document indicators and file extensions
    cleaned = title.replace("Chapter", "").replace("Section", "").replace(".pdf", "").replace(".pptx", "").replace(".docx", "").strip()
    
    # Take first few meaningful words as topic
    words = [word for word in cleaned.split()[:3] if len(word) > 2]
    return " ".join(words) if words else "General Topic"
