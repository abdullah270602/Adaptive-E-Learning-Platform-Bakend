from psycopg2.extras import DictCursor
from uuid import UUID
from psycopg2.extensions import connection as PGConnection
import json
from typing import Optional, List, Dict


def save_user_quiz(
    conn: PGConnection,
    user_id: str,
    doc_id: Optional[str],
    num_mcqs: int,
    mcq_data: List[Dict]
) -> str:
    """
    Save MCQs to database
    Returns: quiz_id (UUID as string)
    """
    query = """
    INSERT INTO user_quizzes (user_id, doc_id, num_mcqs, mcq_data)
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """
    
    with conn.cursor() as cursor:
        cursor.execute(
            query,
            (user_id, doc_id, num_mcqs, json.dumps(mcq_data))
        )
        quiz_id = cursor.fetchone()[0]
        conn.commit()
        return str(quiz_id)

def get_user_quiz(conn: PGConnection, quiz_id: str, user_id: str) -> dict | None:
    """
    Retrieve specific quiz for download
    Returns: Quiz data or None if not found
    """
    query = """
    SELECT id, user_id, doc_id, num_mcqs, mcq_data, created_at
    FROM user_quizzes 
    WHERE id = %s AND user_id = %s;
    """
    
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (quiz_id, user_id))
        result = cursor.fetchone()
        
        if result:
            quiz_data = dict(result)
            # Parse JSON string back to list
            if isinstance(quiz_data['mcq_data'], str):
                quiz_data['mcq_data'] = json.loads(quiz_data['mcq_data'])
            quiz_data['id'] = str(quiz_data['id'])
            return quiz_data
        return None


def get_user_latest_quiz(conn: PGConnection, user_id: str) -> dict | None:
    """
    Retrieve the most recently generated quiz for a user
    Returns: Latest quiz data or None if not found
    """
    query = """
    SELECT id, user_id, doc_id, num_mcqs, mcq_data, created_at
    FROM user_quizzes 
    WHERE user_id = %s 
    ORDER BY created_at DESC 
    LIMIT 1;
    """
    
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        if result:
            quiz_data = dict(result)
            # Parse JSON string back to list
            if isinstance(quiz_data['mcq_data'], str):
                quiz_data['mcq_data'] = json.loads(quiz_data['mcq_data'])
            quiz_data['id'] = str(quiz_data['id'])
            return quiz_data
        return None


def get_all_user_quizzes(conn: PGConnection, user_id: str) -> List[Dict]:
    """
    Get all quizzes for a user (for listing purposes)
    Returns: List of quiz summaries
    """
    query = """
    SELECT id, doc_id, num_mcqs, created_at
    FROM user_quizzes 
    WHERE user_id = %s 
    ORDER BY created_at DESC;
    """
    
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        
        return [
            {
                "id": str(row["id"]),
                "doc_id": row["doc_id"],
                "num_mcqs": row["num_mcqs"],
                "created_at": row["created_at"]
            }
            for row in results
        ]

def delete_user_quiz(conn: PGConnection, quiz_id: str, user_id: str) -> bool:
    """
    Delete specific quiz
    Returns: True if deleted, False if not found
    """
    query = """
    DELETE FROM user_quizzes 
    WHERE id = %s AND user_id = %s
    RETURNING id;
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query, (quiz_id, user_id))
        deleted_id = cursor.fetchone()
        conn.commit()
        return deleted_id is not None

def delete_all_user_quizzes(conn: PGConnection, user_id: str) -> int:
    """
    Delete all quizzes for a user
    Returns: Number of deleted quizzes
    """
    query = """
    DELETE FROM user_quizzes 
    WHERE user_id = %s;
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query, (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count

def quiz_exists(conn: PGConnection, quiz_id: str, user_id: str) -> bool:
    """
    Check if quiz exists for user
    Returns: True if exists, False otherwise
    """
    query = """
    SELECT 1 FROM user_quizzes 
    WHERE id = %s AND user_id = %s 
    LIMIT 1;
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query, (quiz_id, user_id))
        return cursor.fetchone() is not None

def get_quiz_count_by_user(conn: PGConnection, user_id: str) -> int:
    """
    Get total number of quizzes for a user
    Returns: Count of quizzes
    """
    query = "SELECT COUNT(*) FROM user_quizzes WHERE user_id = %s;"
    
    with conn.cursor() as cursor:
        cursor.execute(query, (user_id,))
        return cursor.fetchone()[0]