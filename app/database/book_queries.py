from typing import List, Optional
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
            sections = chapter.get("sections", [])

            if not sections:
                # Fallback section using the chapter itself
                fallback_section = {
                    "title": chapter_title,
                    "page": chapter.get("page", None),  # Optional fallback
                }
                sections = [fallback_section]

            for section in sections:
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

    return [{"type": "book", **dict(row)} for row in results]


def get_book_structure_depreciated(conn: PGConnection, book_id: UUID) -> dict:
    query = """
        SELECT 
            c.id as chapter_id,
            c.chapter_number,
            c.title as chapter_title,
            c.created_at as chapter_created_at,
            s.id as section_id,
            s.title as section_title,
            s.page,
            s.s3_key,
            s.embedding_id,
            s.added_date
        FROM chapters c
        LEFT JOIN sections s ON c.id = s.chapter_id
        WHERE c.book_id = %s
        ORDER BY c.chapter_number::INT, s.page;
    """

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (str(book_id),))
        rows = cursor.fetchall()

    chapters_map = {}
    for row in rows:
        chap_id = row["chapter_id"]
        if chap_id not in chapters_map:
            chapters_map[chap_id] = {
                "chapter_id": chap_id,
                "chapter_number": row["chapter_number"],
                "title": row["chapter_title"],
                "created_at": row["chapter_created_at"],
                "sections": []
            }

        if row["section_id"]:
            chapters_map[chap_id]["sections"].append({
                "id": row["section_id"],
                "chapter_id": chap_id,
                "title": row["section_title"],
                "page": row["page"],
                "s3_key": row["s3_key"],
                "embedding_id": row["embedding_id"],
                "added_date": row["added_date"]
            })

    return {
        "book_id": book_id,
        "chapters": list(chapters_map.values())
    }


def get_book_structure_query(conn, book_id: UUID) -> Optional[dict]:
    query = """
    SELECT 
      b.id AS book_id,
      json_agg(
        json_build_object(
          'chapter_id', c.id,
          'chapter_number', c.chapter_number,
          'title', c.title,
          'sections', (
            SELECT json_agg(
              json_build_object(
                'section_id', s.id,
                'title', s.title,
                'page', s.page
              )
            )
            FROM sections s
            WHERE s.chapter_id = c.id
          )
        )
      ) AS chapters
    FROM books b
    JOIN chapters c ON c.book_id = b.id
    WHERE b.id = %s
    GROUP BY b.id;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (str(book_id),))
        result = cursor.fetchone()

    return dict(result) if result else None


def get_section_content_query(conn: PGConnection, section_id: UUID) -> dict:
    query = """
        SELECT id, chapter_id, title, page, s3_key, embedding_id, added_date
        FROM sections
        WHERE id = %s;
    """

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (str(section_id),))
        row = cursor.fetchone()

    if not row:
        raise ValueError("Section not found")

    return dict(row)


def delete_book_by_id(conn: PGConnection, book_id: str, user_id: str) -> None:
    query = "DELETE FROM books WHERE id = %s AND user_id = %s;"
    with conn.cursor() as cursor:
        cursor.execute(query, (book_id, user_id))
    conn.commit()


def get_book_by_id(conn: PGConnection, book_id: str, user_id: str) -> Optional[dict]:
    query = "SELECT * FROM books WHERE id = %s AND user_id = %s;"
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (book_id, user_id))
        result = cursor.fetchone()
    return dict(result) if result else None


def get_book_metadata(conn: PGConnection, book_id: str) -> Optional[dict]:
    query = """
    SELECT id, user_id, title, file_name, s3_key, created_at
    FROM books
    WHERE id = %s;
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (book_id,))
        result = cursor.fetchone()

    return dict(result) if result else {}
