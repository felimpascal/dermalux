import secrets
from app.db import get_db


class UserMgmtRepository:

    # =========================
    # LIST USERS
    # =========================
    @staticmethod
    def list_users(q: str = ""):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            public_id,
            username,
            nama,
            role,
            is_active,
            created_at
        FROM app_user
        WHERE (
            %s = ''
            OR username LIKE CONCAT('%%', %s, '%%')
            OR nama LIKE CONCAT('%%', %s, '%%')
        )
        ORDER BY username
        """

        cursor.execute(sql, (q, q, q))
        return cursor.fetchall()

    # =========================
    # GET USER
    # =========================
    @staticmethod
    def get_user(user_id: int):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            public_id,
            username,
            nama,
            role,
            is_active,
            created_at
        FROM app_user
        WHERE id = %s
        """

        cursor.execute(sql, (user_id,))
        return cursor.fetchone()

    # =========================
    # INSERT USER
    # =========================
    @staticmethod
    def insert_user(nama, username, password_hash, role, is_active):
        db = get_db()
        cursor = db.cursor()

        # generate public id
        public_id = "usr_" + secrets.token_hex(4)

        sql = """
        INSERT INTO app_user
        (
            public_id,
            username,
            nama,
            password_hash,
            role,
            is_active,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """

        cursor.execute(
            sql,
            (
                public_id,
                username,
                nama,
                password_hash,
                role,
                is_active
            )
        )

        db.commit()

    # =========================
    # UPDATE USER (NO PASSWORD)
    # =========================
    @staticmethod
    def update_user(user_id, nama, username, role, is_active):
        db = get_db()
        cursor = db.cursor()

        sql = """
        UPDATE app_user
        SET
            nama = %s,
            username = %s,
            role = %s,
            is_active = %s
        WHERE id = %s
        """

        cursor.execute(sql, (nama, username, role, is_active, user_id))
        db.commit()

    # =========================
    # UPDATE PASSWORD
    # =========================
    @staticmethod
    def update_password(user_id, password_hash):
        db = get_db()
        cursor = db.cursor()

        sql = """
        UPDATE app_user
        SET password_hash = %s
        WHERE id = %s
        """

        cursor.execute(sql, (password_hash, user_id))
        db.commit()

    # =========================
    # GET PERMISSION + GRANTED
    # =========================
    @staticmethod
    def get_permissions_with_granted(user_id):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = """
        SELECT
            p.id,
            p.permission_code,
            p.permission_name,
            CASE
                WHEN m.permission_id IS NULL THEN 0
                ELSE 1
            END AS granted
        FROM web_api_permission p
        LEFT JOIN web_user_api_permission m
            ON m.permission_id = p.id
            AND m.user_id = %s
        WHERE p.is_active = 1
        ORDER BY p.permission_code
        """

        cursor.execute(sql, (user_id,))
        return cursor.fetchall()

    # =========================
    # DELETE USER PERMISSIONS
    # =========================
    @staticmethod
    def delete_user_permissions(user_id):
        db = get_db()
        cursor = db.cursor()

        sql = """
        DELETE FROM web_user_api_permission
        WHERE user_id = %s
        """

        cursor.execute(sql, (user_id,))
        db.commit()

    # =========================
    # INSERT USER PERMISSIONS
    # =========================
    @staticmethod
    def insert_user_permissions(user_id, perm_ids):
        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute(
                "DELETE FROM web_user_api_permission WHERE user_id = %s",
                (user_id,)
            )
            db.commit()

            unique_perm_ids = list(dict.fromkeys(perm_ids))

            sql = """
            INSERT INTO web_user_api_permission
            (user_id, permission_id)
            VALUES (%s, %s)
            """

            for pid in unique_perm_ids:
                cursor.execute(sql, (user_id, pid))

            db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            cursor.close()

    # =========================
    # REPLACE PERMISSIONS
    # =========================
    @staticmethod
    def replace_permissions(user_id, perm_ids):
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "DELETE FROM web_user_api_permission WHERE user_id = %s",
            (user_id,)
        )

        if perm_ids:
            sql = """
            INSERT INTO web_user_api_permission
            (user_id, permission_id)
            VALUES (%s, %s)
            """

            for pid in perm_ids:
                cursor.execute(sql, (user_id, pid))

        db.commit()

    # =========================
    # GET USER BY PUBLIC ID
    # =========================
    @staticmethod
    def get_user_by_public_id(public_id: str):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            public_id,
            username,
            nama,
            role,
            is_active,
            created_at
        FROM app_user
        WHERE public_id = %s
        """

        cursor.execute(sql, (public_id,))
        return cursor.fetchone()