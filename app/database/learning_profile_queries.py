from psycopg2.extras import DictCursor
from uuid import UUID
from psycopg2.extensions import connection as PGConnection


def save_learning_profile(
    conn: PGConnection,
    user_id: UUID,
    visual: float,
    reading: float,
    kinesthetic: float,
    primary_style: str,
    description: str
):
    query = """
    INSERT INTO learning_profiles (
        user_id, visual_score, reading_score,
        kinesthetic_score, primary_style, description
    )
    VALUES (
        %s, %s, %s, %s, %s, %s
    );
    """

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            query,
            (str(user_id), visual, reading, kinesthetic, primary_style, description)
        )
        conn.commit()


def has_learning_profile(conn: PGConnection, user_id: str) -> bool:
    query = "SELECT 1 FROM learning_profiles WHERE user_id = %s LIMIT 1;"
    with conn.cursor() as cursor:
        cursor.execute(query, (user_id,))
        return cursor.fetchone() is not None
