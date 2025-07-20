from typing import List, Optional
from uuid import UUID, uuid4
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import DictCursor
from datetime import datetime


def create_note_query(
    conn: PGConnection,
    user_id: UUID,
    title: str,
    filename: str,
    s3_key: str
) -> str:
    note_id = str(uuid4())
    query = """
        INSERT INTO notes (
            id, user_id, title, filename, s3_key, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING id;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (
            note_id, user_id, title, filename, s3_key
        ))
        conn.commit()
        return cursor.fetchone()["id"]


def get_notes_by_user(conn: PGConnection, user_id: UUID) -> List[dict]:
    query = """
        SELECT id, title, created_at
        FROM notes
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (str(user_id),))
        results = cursor.fetchall()
    return [{"type": "note", **dict(row)} for row in results]


def delete_note_by_id(conn: PGConnection, note_id: str, user_id: str) -> None:
    query = "DELETE FROM notes WHERE id = %s AND user_id = %s;"
    with conn.cursor() as cursor:
        cursor.execute(query, (note_id, user_id))
    conn.commit()


def get_note_by_id(conn: PGConnection, note_id: str, user_id: str) -> Optional[dict]:
    query = "SELECT * FROM notes WHERE id = %s AND user_id = %s;"
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (note_id, user_id))
        result = cursor.fetchone()
    return dict(result) if result else None


def get_note_metadata(conn: PGConnection, note_id: str) -> Optional[dict]:
    query = """
        SELECT id, user_id, title, filename, s3_key, created_at, updated_at
        FROM notes
        WHERE id = %s;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (note_id,))
        result = cursor.fetchone()
    return dict(result) if result else None
