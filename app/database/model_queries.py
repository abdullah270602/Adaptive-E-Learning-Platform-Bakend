from psycopg2.extras import DictCursor
from uuid import UUID
from psycopg2.extensions import connection as PGConnection


def get_all_models(conn: PGConnection) -> list:
    """
    List all available active models.
    """
    query = """
        SELECT
            id,
            display_name,
            model_name
        FROM models
        WHERE is_active = TRUE;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def get_all_models_services(conn: PGConnection) -> list:
    """
    List all available active models and their services.
    """
    query = """
        SELECT
            id,
            display_name,
            service,
            model_name
        FROM models
        WHERE is_active = TRUE;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    
    
def get_active_model_name_and_service_by_id(conn: PGConnection, model_id: UUID) -> str:
    """
    Retrieve the model name and provider by its ID.
    """
    query = """
    SELECT model_name, service
    FROM models
    WHERE id = %s AND is_active = TRUE;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (model_id,))
        result = cursor.fetchone()
        return result