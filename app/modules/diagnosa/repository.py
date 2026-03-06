from app.db import get_db

class DiagnosaRepository:

    @staticmethod
    def list_diagnosa(search: str | None = None, active_only: bool = False):
        db = get_db()
        cur = db.cursor(dictionary=True)

        where = []
        params = {}

        if search:
            where.append("(diagnosa_code LIKE %(q)s OR diagnosa_name LIKE %(q)s)")
            params["q"] = f"%{search.strip()}%"

        if active_only:
            where.append("is_active = 1")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sql = f"""
        SELECT id, diagnosa_code, diagnosa_name, is_active, created_at, updated_at
        FROM master_diagnosa
        {where_sql}
        ORDER BY is_active DESC, diagnosa_code ASC
        """
        cur.execute(sql, params)
        return cur.fetchall()

    @staticmethod
    def get_by_id(diagnosa_id: int):
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM master_diagnosa WHERE id=%s", (diagnosa_id,))
        return cur.fetchone()

    @staticmethod
    def get_by_code(diagnosa_code: str):
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM master_diagnosa WHERE diagnosa_code=%s", (diagnosa_code,))
        return cur.fetchone()

    @staticmethod
    def insert(payload: dict):
        db = get_db()
        cur = db.cursor()
        sql = """
        INSERT INTO master_diagnosa (diagnosa_code, diagnosa_name, is_active)
        VALUES (%s,%s,%s)
        """
        cur.execute(sql, (payload["diagnosa_code"], payload["diagnosa_name"], payload["is_active"]))
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(diagnosa_id: int, payload: dict):
        db = get_db()
        cur = db.cursor()
        sql = """
        UPDATE master_diagnosa
        SET diagnosa_code=%s, diagnosa_name=%s, is_active=%s
        WHERE id=%s
        """
        cur.execute(sql, (payload["diagnosa_code"], payload["diagnosa_name"], payload["is_active"], diagnosa_id))
        db.commit()
        return cur.rowcount

    @staticmethod
    def set_active(diagnosa_id: int, is_active: int):
        db = get_db()
        cur = db.cursor()
        cur.execute("UPDATE master_diagnosa SET is_active=%s WHERE id=%s", (is_active, diagnosa_id))
        db.commit()
        return cur.rowcount