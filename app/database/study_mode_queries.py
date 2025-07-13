from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import DictCursor
from uuid import UUID, uuid4
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


def insert_chat_messages(conn: PGConnection, messages: list[dict]):
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        for msg in messages:
            cursor.execute(
                """
                INSERT INTO chat_messages (
                    id, chat_session_id, role, content, model_id, 
                    tool_response_id, tool_type, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(msg["id"]), msg["chat_session_id"], msg["role"],
                    msg["content"], msg.get("model_id"),
                    msg.get("tool_response_id"), msg.get("tool_type"), msg["created_at"]
                )
            )
        conn.commit()

def get_last_chat_messages(conn: PGConnection, chat_session_id: UUID, limit: int = 10) -> list[dict]:
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE chat_session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (str(chat_session_id), limit)
        )
        messages = cursor.fetchall()
        # Reverse to chronological order (oldest first)
        return list(reversed(messages))
