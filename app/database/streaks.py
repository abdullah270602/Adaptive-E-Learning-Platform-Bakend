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

def get_leaderboard_with_user_position(conn: PGConnection, user_id: str, limit: int = 5) -> dict:
    """
    Get top users and specific user position in leaderboard
    Returns top N users + user's position if not in top N
    """
    with conn.cursor(cursor_factory=DictCursor) as cursor:

        cursor.execute("""
            WITH ranked_users AS (
                SELECT 
                    us.user_id,
                    u.name,
                    u.email,
                    us.current_streak,
                    us.longest_streak,
                    us.last_active_date,
                    ROW_NUMBER() OVER (ORDER BY us.current_streak DESC, us.longest_streak DESC, us.last_active_date DESC) as rank
                FROM user_streaks us
                JOIN users u ON us.user_id = u.id
                WHERE us.current_streak > 0  -- Only active streaks
                ORDER BY us.current_streak DESC, us.longest_streak DESC, us.last_active_date DESC
            )
            SELECT * FROM ranked_users
            WHERE rank <= %s OR user_id = %s
            ORDER BY rank
        """, (limit, user_id))
        
        all_results = cursor.fetchall()
        
        # Separate top users from current user
        top_users = []
        user_position = None
        
        for row in all_results:
            row_dict = dict(row)
            if row_dict['rank'] <= limit:
                top_users.append(row_dict)
            if row_dict['user_id'] == user_id:
                user_position = row_dict
        
        # If user not found in streaks, get their position as 0
        if not user_position:
            cursor.execute("""
                SELECT COUNT(*) + 1 as rank
                FROM user_streaks 
                WHERE current_streak > 0
            """)
            total_active = cursor.fetchone()['rank']
            
            cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()
            
            user_position = {
                'user_id': user_id,
                'name': user_info['name'] if user_info else 'Unknown',
                'email': user_info['email'] if user_info else 'Unknown',
                'current_streak': 0,
                'longest_streak': 0,
                'last_active_date': None,
                'rank': total_active
            }
        
        return {
            'top_users': top_users,
            'user_position': user_position,
            'total_active_users': len(top_users) if user_position['rank'] <= limit else len(top_users) + 1
        }
