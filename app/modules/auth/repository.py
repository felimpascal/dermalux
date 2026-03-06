import hashlib
from app.db import get_db


def sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


class AuthRepository:
    @staticmethod
    def get_user_by_username(username: str) -> dict | None:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, username, nama, password_hash, role, is_active
            FROM app_user
            WHERE username=%s
            LIMIT 1
            """,
            (username,),
        )
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def update_password(user_id: int, new_password: str) -> None:
        new_hash = sha256(new_password)
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "UPDATE app_user SET password_hash=%s WHERE id=%s",
            (new_hash, user_id),
        )
        db.commit()
        cur.close()