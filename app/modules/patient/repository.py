from typing import Dict, List, Optional
from app.db import get_db

class PatientRepository:
    @staticmethod
    def insert(
        nik,
        full_name,
        birth_place,
        birth_date,
        gender,
        address,
        phone
    ):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        INSERT INTO patient
        (nik, full_name, birth_place, birth_date, gender, address, phone)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        cur.execute(sql, (
            nik,
            full_name,
            birth_place,
            birth_date,
            gender,
            address,
            phone
        ))

        db.commit()
        patient_id = cur.lastrowid

        cur.execute("SELECT * FROM patient WHERE id=%s", (patient_id,))
        row = cur.fetchone()
        cur.close()

        return row

    @staticmethod
    def search(q: str):
        db = get_db()
        cur = db.cursor(dictionary=True)

        if not q:
            cur.execute("SELECT * FROM patient ORDER BY id DESC LIMIT 50")
        else:
            like = f"%{q}%"
            cur.execute(
                """
                SELECT * FROM patient
                WHERE full_name LIKE %s OR phone LIKE %s
                ORDER BY id DESC
                LIMIT 50
                """,
                (like, like),
            )
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_by_id(patient_id: str):
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM patient WHERE id=%s", (patient_id,))
        row = cur.fetchone()
        cur.close()
        return row
    
    @staticmethod
    def update(patient_id: int, nik, full_name, birth_place, birth_date, gender, address, phone):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        UPDATE patient
        SET
            nik=%s,
            full_name=%s,
            birth_place=%s,
            birth_date=%s,
            gender=%s,
            address=%s,
            phone=%s
        WHERE id=%s
        """
        cur.execute(sql, (nik, full_name, birth_place, birth_date, gender, address, phone, patient_id))
        db.commit()

        cur.execute("SELECT * FROM patient WHERE id=%s", (patient_id,))
        row = cur.fetchone()
        cur.close()
        return row
    
    @staticmethod
    def search(q: str = "", limit: int = 20) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        q = (q or "").strip()
        limit = max(1, min(int(limit or 20), 50))  # batasi max 50 biar aman

        sql = """
        SELECT
            id,
            patient_code,
            nik,
            full_name,
            birth_place,
            phone,
            gender,
            birth_date,
            address
        FROM patient
        WHERE 1=1
        """
        params = []

        if q:
            # Cari by beberapa kolom yang paling relevan untuk lookup
            sql += """
            AND (
                patient_code LIKE %s
                OR nik LIKE %s
                OR full_name LIKE %s
                OR phone LIKE %s
            )
            """
            s = f"%{q}%"
            params += [s, s, s, s]

        sql += """
        ORDER BY full_name ASC
        LIMIT %s
        """
        params.append(limit)

        cur.execute(sql, params)
        return cur.fetchall()

    @staticmethod
    def get_by_code(patient_code: str) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        patient_code = (patient_code or "").strip()
        if not patient_code:
            return None

        sql = """
        SELECT
            patient_code,
            nik,
            full_name,
            birth_place,
            phone,
            gender,
            birth_date,
            address
        FROM patient
        WHERE patient_code = %s
        LIMIT 1
        """
        cur.execute(sql, (patient_code,))
        return cur.fetchone()