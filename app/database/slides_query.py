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
