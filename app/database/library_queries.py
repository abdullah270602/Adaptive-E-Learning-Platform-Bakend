from typing import Dict, List, Optional
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection as PGConnection
from app.cache.metadata import get_cached_doc_metadata
import logging

logger = logging.getLogger(__name__)


def get_documents_metadata_by_ids(
    conn: PGConnection, doc_ids: List[str], user_id: str
) -> Dict:
    """
    Get metadata for multiple documents by their IDs using cached metadata
    """
    if not doc_ids:
        return {}

    documents = {}

    # First, try to determine document types for each ID
    doc_types_map = get_document_types_by_ids(conn, doc_ids, user_id)

    # Debug logging
    logger.info(f"Document type mapping: {doc_types_map}")
    logger.info(f"Requested doc_ids: {doc_ids}")

    # Use cached metadata for each document
    for doc_id in doc_ids:
        doc_type = doc_types_map.get(doc_id)
        if doc_type:
            try:
                metadata = get_cached_doc_metadata(conn, doc_id, doc_type)
                if metadata:
                    # Ensure we have the document_type in metadata
                    metadata["document_type"] = doc_type
                    documents[doc_id] = metadata
                    logger.info(
                        f"Successfully retrieved metadata for {doc_id} (type: {doc_type})"
                    )
                else:
                    logger.warning(
                        f"No cached metadata found for {doc_id} (type: {doc_type})"
                    )
            except Exception as e:
                logger.warning(f"Failed to get cached metadata for {doc_id}: {e}")
        else:
            logger.warning(
                f"No document type found for {doc_id} - document may not exist in database"
            )

    return documents


def get_document_types_by_ids(
    conn: PGConnection, doc_ids: List[str], user_id: str
) -> Dict[str, str]:
    """
    Determine document types for given document IDs
    """
    if not doc_ids:
        return {}

    doc_types = {}

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        # Check books
        cursor.execute(
            """
            SELECT id FROM books 
            WHERE id = ANY(%s) AND user_id = %s
        """,
            (doc_ids, user_id),
        )

        book_results = cursor.fetchall()
        logger.info(
            f"Found {len(book_results)} books for doc_ids: {[str(row['id']) for row in book_results]}"
        )
        for row in book_results:
            doc_types[str(row["id"])] = "book"

        # Check presentations
        cursor.execute(
            """
            SELECT id FROM presentations 
            WHERE id = ANY(%s) AND user_id = %s
        """,
            (doc_ids, user_id),
        )

        presentation_results = cursor.fetchall()
        logger.info(
            f"Found {len(presentation_results)} presentations for doc_ids: {[str(row['id']) for row in presentation_results]}"
        )
        for row in presentation_results:
            doc_types[str(row["id"])] = "presentation"

        # Check notes
        cursor.execute(
            """
            SELECT id FROM notes 
            WHERE id = ANY(%s) AND user_id = %s
        """,
            (doc_ids, user_id),
        )

        notes_results = cursor.fetchall()
        logger.info(
            f"Found {len(notes_results)} notes for doc_ids: {[str(row['id']) for row in notes_results]}"
        )
        for row in notes_results:
            doc_types[str(row["id"])] = "notes"

    logger.info(f"Final doc_types mapping: {doc_types}")
    return doc_types


def get_user_document_counts(conn: PGConnection, user_id: str) -> Dict:
    """Get count of documents by type for a user"""
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        counts = {"books": 0, "presentations": 0, "notes": 0}

        # Count books
        cursor.execute(
            "SELECT COUNT(*) as count FROM books WHERE user_id = %s", (user_id,)
        )
        counts["books"] = cursor.fetchone()["count"]

        # Count presentations
        cursor.execute(
            "SELECT COUNT(*) as count FROM presentations WHERE user_id = %s", (user_id,)
        )
        counts["presentations"] = cursor.fetchone()["count"]

        # Count notes
        cursor.execute(
            "SELECT COUNT(*) as count FROM notes WHERE user_id = %s", (user_id,)
        )
        counts["notes"] = cursor.fetchone()["count"]

        counts["total"] = sum(counts.values())
        return counts
