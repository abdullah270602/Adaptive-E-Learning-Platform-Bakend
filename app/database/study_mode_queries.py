from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import DictCursor
from uuid import uuid4
from app.schemas.chat import ChatMessageCreate


def get_or_create_chat_session(
    conn: PGConnection, user_id: str, document_id: str, document_type: str
) -> dict:
    query_select = """
        SELECT * FROM chat_sessions
        WHERE user_id = %s AND document_id = %s AND document_type = %s
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query_select, (user_id, document_id, document_type))
        session = cursor.fetchone()
        if session:
            return dict(session)

        query_insert = """
            INSERT INTO chat_sessions (id, user_id, document_id, document_type)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """
        new_id = str(uuid4())
        cursor.execute(query_insert, (new_id, user_id, document_id, document_type))
        conn.commit()
        return dict(cursor.fetchone())


def get_last_position(
    conn: PGConnection, user_id: str, document_id: str, document_type: str
) -> dict:
    query = """
        SELECT page_number, chapter_id, section_id, updated_at
        FROM document_progress
        WHERE user_id = %s AND document_id = %s AND document_type = %s
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (user_id, document_id, document_type))
        result = cursor.fetchone()
    return dict(result) if result else {}


def update_document_progress(
    conn: PGConnection,
    user_id: str,
    document_id: str,
    document_type: str,
    page_number: int,
    section_id: str,
    chapter_id: str,
) -> None:
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            INSERT INTO document_progress (
                user_id, document_id, document_type,
                page_number, section_id, chapter_id, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id, document_id) DO UPDATE SET
                page_number = EXCLUDED.page_number,
                section_id = EXCLUDED.section_id,
                chapter_id = EXCLUDED.chapter_id,
                updated_at = NOW()
            """,
            (
                str(user_id),
                str(document_id),
                document_type,
                page_number,
                str(section_id) if section_id else None,
                str(chapter_id) if chapter_id else None,
            ),
        )
        conn.commit()


def insert_chat_message(
    conn: PGConnection, data: ChatMessageCreate, role: str = "user"
) -> dict:
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            INSERT INTO chat_messages (
                chat_session_id, role, content, model_id
            )
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (
                str(data.chat_session_id),
                role,
                data.content,
                str(data.model_id) if data.model_id else None,
            ),
        )
        result = cursor.fetchone()
    
    conn.commit()
    
    return dict(result)
