from typing import Optional
from psycopg2.extensions import connection as PGConnection

from app.database.book_queries import get_book_metadata
from app.database.notes_queries import get_note_metadata
from app.database.slides_queries import get_slide_metadata


def get_doc_metadata(conn: PGConnection, document_id: str, document_type: str) -> Optional[dict]:
    if document_type == "book":
        return get_book_metadata(conn, document_id)
    elif document_type == "slides" or document_type == "presentation":
        return get_slide_metadata(conn, document_id)
    elif document_type == "notes":
        return get_note_metadata(conn, document_id)
    else:
        raise ValueError(f"Unknown document type: {document_type}")