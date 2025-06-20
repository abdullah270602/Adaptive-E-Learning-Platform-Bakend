from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import DictCursor
from app.services.utils import extract_chapter_number


def create_book_query(
    conn: PGConnection,
    user_id: UUID,
    book_id: UUID,
    title: str,
    file_name: str,
    s3_key: str
) -> dict:
    query = """
    INSERT INTO books (id, user_id, title, file_name, file_id, s3_key)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, title, file_name, s3_key, created_at;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (book_id, user_id, title, file_name, book_id, s3_key))
        result = cursor.fetchone()
    conn.commit()
    return dict(result)


def create_book_structure(
    conn: PGConnection, book_id: str, toc_structure: dict, s3_key: str
) -> dict:
    chapter_collection = []
    section_collection = []

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        for chapter in toc_structure.get("chapters", []):
            chapter_id = str(uuid4())
            chapter_title = chapter.get("title", "Untitled Chapter")
            chapter_number = extract_chapter_number(chapter_title)
            
            # Insert chapter
            cursor.execute(
                """
                INSERT INTO chapters (id, book_id, chapter_number, title)
                VALUES (%s, %s, %s, %s)
            """,
                (chapter_id, book_id, chapter_number, chapter_title),
            )

            section_ids = []

            for section in chapter.get("sections", []):
                section_id = str(uuid4())
                section_title = section.get("title", "Untitled Section")
                section_page = section.get("page", None)

                # Insert section
                cursor.execute(
                    """
                    INSERT INTO sections (id, chapter_id, title, page, s3_key)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (section_id, chapter_id, section_title, section_page, s3_key),
                )

                section_collection.append(
                    {
                        "section_id": section_id,
                        "title": section_title,
                        "page": section_page,
                        "s3_key": s3_key,
                    }
                )

                section_ids.append(section_id)

            chapter_collection.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "title": chapter_title,
                    "sections": section_ids,
                }
            )

        conn.commit()

    return {
        "book_id": book_id,
        "chapter_collections": chapter_collection,
        "section_collections": section_collection,
    }


def get_books_by_user(conn: PGConnection, user_id: str) -> List[dict]:
    query = """
        SELECT id, title, file_name, file_id, s3_key, created_at
        FROM books
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()

    return [dict(row) for row in results]
