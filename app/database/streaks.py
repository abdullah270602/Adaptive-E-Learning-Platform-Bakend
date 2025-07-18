from datetime import date, timedelta
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection as PGConnection

def update_user_streak(conn: PGConnection, user_id: str) -> dict:
    today = date.today()

    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute("SELECT * FROM user_streaks WHERE user_id = %s", (user_id,))
        streak = cursor.fetchone()

        if streak:
            last_active = streak["last_active_date"]
            current_streak = streak["current_streak"]

            if last_active == today:
                current_streak += 1
                return {"current_streak": current_streak, "updated": False}

            elif last_active == today - timedelta(days=1):
                current_streak += 1
            else:
                current_streak = 1

            longest = max(current_streak, streak["longest_streak"])

            cursor.execute("""
                UPDATE user_streaks
                SET current_streak = %s, last_active_date = %s, longest_streak = %s, updated_at = NOW()
                WHERE user_id = %s
                RETURNING current_streak, longest_streak, last_active_date
            """, (current_streak, today, longest, user_id))
        else:
            current_streak = 1
            cursor.execute("""
                INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_active_date)
                VALUES (%s, %s, %s, %s)
                RETURNING current_streak, longest_streak, last_active_date
            """, (user_id, current_streak, current_streak, today))

        result = cursor.fetchone()
        conn.commit()
        return {
            "current_streak": result["current_streak"],
            "longest_streak": result["longest_streak"],
            "last_active_date": result["last_active_date"],
            "updated": True
        }

def get_user_streak(conn: PGConnection, user_id: str) -> dict:
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute("SELECT * FROM user_streaks WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            return dict(result)
        return {
            "user_id": user_id,
            "current_streak": 0,
            "longest_streak": 0,
            "last_active_date": None,
            "created_at": None,
            "updated_at": None
        }
