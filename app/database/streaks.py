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
                # print(" TESTING Streak updated")
                # current_streak += 1
                return {"current_streak": current_streak, "updated": False} #FIXME un comment this line later

            elif last_active == today - timedelta(days=1):
                current_streak += 1
            else:
                current_streak = 1

            longest = max(current_streak, streak["longest_streak"])

            cursor.execute("""
                UPDATE user_streaks
                SET current_streak = %s, last_active_date = %s, longest_streak = %s, updated_at = NOW()
                WHERE user_id = %s
            """, (current_streak, today, longest, user_id))
        else:
            current_streak = 1
            cursor.execute("""
                INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_active_date)
                VALUES (%s, %s, %s, %s)
            """, (user_id, current_streak, current_streak, today))

        conn.commit()
        return {"current_streak": current_streak, "updated": True}

def get_user_streak(conn: PGConnection, user_id: str) -> dict:
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute("SELECT * FROM user_streaks WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return dict(result) if result else {}
