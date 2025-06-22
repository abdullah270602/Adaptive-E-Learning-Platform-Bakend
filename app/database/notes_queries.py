# def delete_notes_by_id(conn: PGConnection, notes_id: str, user_id: str) -> None:
#     query = "DELETE FROM notes WHERE id = %s AND user_id = %s;"
#     with conn.cursor() as cursor:
#         cursor.execute(query, (notes_id, user_id))
#     conn.commit()


# def get_notes_by_id(conn: PGConnection, notes_id: str, user_id: str) -> Optional[dict]:
#     query = "SELECT * FROM notes WHERE id = %s AND user_id = %s;"
#     with conn.cursor(cursor_factory=DictCursor) as cursor:
#         cursor.execute(query, (notes_id, user_id))
#         result = cursor.fetchone()
#     return dict(result) if result else None