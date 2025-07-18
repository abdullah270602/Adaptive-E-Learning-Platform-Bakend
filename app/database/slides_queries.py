from typing import List, Optional
from uuid import UUID, uuid4
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import DictCursor

def create_slide_query(
    conn: PGConnection,
    user_id: UUID,
    title: str,
    original_filename: str,
    s3_key: str,
    total_slides: int,
    has_speaker_notes: bool
) -> str:
    presentation_id = str(uuid4())

    query = """
        INSERT INTO presentations (
            id, user_id, title, original_filename, s3_key, total_slides, has_speaker_notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (
            presentation_id,
            user_id,
            title,
            original_filename,
            s3_key,
            total_slides,
            has_speaker_notes
        ))
        conn.commit()
        return cursor.fetchone()["id"]


def get_slides_by_user(conn: PGConnection, user_id: UUID) -> List[dict]:
    query = """
    SELECT id, original_filename,total_slides, has_speaker_notes, created_at
    FROM presentations
    WHERE user_id = %s
    ORDER BY created_at DESC
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (str(user_id),))
        results = cursor.fetchall()

    return [{"type": "presentation", **dict(row)} for row in results]


def delete_slide_by_id(conn: PGConnection, slide_id: str, user_id: str) -> None:
    query = "DELETE FROM presentations WHERE id = %s AND user_id = %s;"
    with conn.cursor() as cursor:
        cursor.execute(query, (slide_id, user_id))
    conn.commit()


def get_slide_by_id(conn: PGConnection, slide_id: str, user_id: str) -> Optional[dict]:
    query = "SELECT * FROM presentations WHERE id = %s AND user_id = %s;"
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (slide_id, user_id))
        result = cursor.fetchone()
    return dict(result) if result else None


def get_slide_metadata(conn: PGConnection, slide_id: str) -> Optional[dict]:
    query = """
    SELECT id, user_id, title, original_filename, total_slides AS total_pages, s3_key, created_at
    FROM presentations
    WHERE id = %s;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (slide_id,))
        result = cursor.fetchone()

    return dict(result) if result else {}
