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
