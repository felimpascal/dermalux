# app/modules/authz/repository.py
from app.db import get_db

class PermissionRepository:
    @staticmethod
    def has_permission_user_id(user_id: int, permission_code: str) -> bool:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
            SELECT 1 AS ok
            FROM web_user_api_permission uap
            JOIN web_api_permission p ON uap.permission_id = p.id
            WHERE uap.user_id = %s
              AND p.permission_code = %s
              AND p.is_active = 1
            LIMIT 1
        """
        cur.execute(sql, (user_id, permission_code))
        row = cur.fetchone()
        cur.close()
        return bool(row)