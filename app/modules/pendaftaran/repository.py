# app/modules/pendaftaran/repository.py

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import secrets
from app.db import get_db


class PendaftaranRepository:

    # =========================
    # Helpers
    # =========================
    @staticmethod
    def _dict_cursor(db):
        return db.cursor(dictionary=True)

    @staticmethod
    def _safe_int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    @staticmethod
    def _safe_float(v, default=0.0):
        try:
            # terima "150000", "150.000", "150,000"
            s = str(v or "").strip()
            s = s.replace(".", "").replace(",", "")
            if not s:
                return default
            return float(s)
        except Exception:
            return default

    # =========================
    # HEADER
    # =========================
    @staticmethod
    def list_headers(search: str = "", status: str = "", date: str = "") -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            p.pendaftaran_id,
            p.patient_code,

            pat.full_name,
            pat.phone,
            pat.birth_date,
            TIMESTAMPDIFF(YEAR, pat.birth_date, DATE(p.tgl_pendaftaran)) AS age_years,

            p.tgl_pendaftaran,
            p.anamnesis_umum,
            p.status,
            p.paidAmount,

            rl.token AS receipt_token,   -- <==== INI

            COALESCE(SUM(pt.subtotal),0) total
        FROM pendaftaran p
        LEFT JOIN patient pat
            ON pat.patient_code COLLATE utf8mb4_unicode_ci
            = p.patient_code   COLLATE utf8mb4_unicode_ci
        LEFT JOIN pendaftaran_treatment pt
            ON pt.pendaftaran_id = p.pendaftaran_id

        LEFT JOIN pendaftaran_receipt_link rl   -- <==== INI
            ON rl.pendaftaran_id = p.pendaftaran_id

        WHERE 1=1
        """

        params: List[Any] = []

        if status:
            sql += " AND p.status=%s"
            params.append(status)

        if date:
            d0 = datetime.strptime(date, "%Y-%m-%d")
            d1 = d0 + timedelta(days=1)
            sql += " AND p.tgl_pendaftaran >= %s AND p.tgl_pendaftaran < %s"
            params += [d0.strftime("%Y-%m-%d 00:00:00"), d1.strftime("%Y-%m-%d 00:00:00")]

        if search:
            sql += """
            AND (
                p.patient_code   COLLATE utf8mb4_unicode_ci LIKE %s
                OR p.anamnesis_umum COLLATE utf8mb4_unicode_ci LIKE %s
                OR CAST(p.pendaftaran_id AS CHAR) COLLATE utf8mb4_unicode_ci LIKE %s
                OR pat.full_name COLLATE utf8mb4_unicode_ci LIKE %s
                OR pat.phone     COLLATE utf8mb4_unicode_ci LIKE %s
            )
            """
            s = f"%{search}%"
            params += [s, s, s, s, s]

        sql += """
        GROUP BY
            p.pendaftaran_id,
            p.patient_code,

            pat.full_name,
            pat.phone,
            pat.birth_date,

            p.tgl_pendaftaran,
            p.anamnesis_umum,
            p.status,
            p.paidAmount,
            rl.token               -- <==== INI
        ORDER BY p.tgl_pendaftaran DESC
        """

        cur.execute(sql, params)
        return cur.fetchall()
    # =========================
    # GET HEADER
    # =========================
    @staticmethod
    def get_header(pendaftaran_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            p.*,

            pat.full_name,
            pat.phone,
            pat.birth_date,
            TIMESTAMPDIFF(YEAR, pat.birth_date, DATE(p.tgl_pendaftaran)) AS age_years,

            COALESCE(SUM(pt.subtotal),0) total
        FROM pendaftaran p
        LEFT JOIN patient pat
            ON pat.patient_code COLLATE utf8mb4_unicode_ci
             = p.patient_code   COLLATE utf8mb4_unicode_ci
        LEFT JOIN pendaftaran_treatment pt
            ON pt.pendaftaran_id = p.pendaftaran_id
        WHERE p.pendaftaran_id=%s
        GROUP BY
            p.pendaftaran_id,
            pat.full_name,
            pat.phone,
            pat.birth_date
        """

        cur.execute(sql, (pendaftaran_id,))
        return cur.fetchone()

    # =========================
    # INSERT HEADER
    # =========================
    @staticmethod
    def insert_header(data: Dict) -> int:
        db = get_db()
        cur = db.cursor()

        sql = """
        INSERT INTO pendaftaran
        (
            patient_code,
            tgl_pendaftaran,
            anamnesis_umum,
            status,
            paidAmount
        )
        VALUES
        (%s,%s,%s,'draft',0)
        """

        cur.execute(
            sql,
            (
                data.get("patient_code"),
                data.get("tgl_pendaftaran"),
                data.get("anamnesis_umum"),
            ),
        )
        db.commit()
        return cur.lastrowid

    # =========================
    # UPDATE HEADER
    # =========================
    @staticmethod
    def update_header(pendaftaran_id: int, data: Dict):
        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE pendaftaran
        SET
            patient_code=%s,
            tgl_pendaftaran=%s,
            anamnesis_umum=%s
        WHERE pendaftaran_id=%s
        """

        cur.execute(
            sql,
            (
                data.get("patient_code"),
                data.get("tgl_pendaftaran"),
                data.get("anamnesis_umum"),
                pendaftaran_id,
            ),
        )
        db.commit()

    # =========================
    # STATUS
    # =========================
    @staticmethod
    def confirm(pendaftaran_id: int):
        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE pendaftaran
        SET status='confirmed'
        WHERE pendaftaran_id=%s
        """
        cur.execute(sql, (pendaftaran_id,))
        db.commit()

    @staticmethod
    def cancel(pendaftaran_id: int):
        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE pendaftaran
        SET status='canceled'
        WHERE pendaftaran_id=%s
        """
        cur.execute(sql, (pendaftaran_id,))
        db.commit()

    @staticmethod
    def set_paid(pendaftaran_id: int, paid_amount):
        """
        Set status -> 'paid' dan isi p.paidAmount (tanpa kolom paidDate).
        paid_amount boleh string "150.000" atau angka.
        """
        amt = PendaftaranRepository._safe_float(paid_amount, default=0.0)
        if amt <= 0:
            # biar jelas error di layer service/route (silakan tangkap di atas)
            raise ValueError("paidAmount harus > 0")

        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE pendaftaran
        SET
            status='paid',
            paidAmount=%s
        WHERE pendaftaran_id=%s
        """
        cur.execute(sql, (amt, pendaftaran_id))
        db.commit()

    @staticmethod
    def unset_paid(pendaftaran_id: int):
        """
        Rollback paid -> confirmed (atau draft bila Anda mau).
        - status: confirmed
        - paidAmount: NULL
        - hapus receipt link bila ada
        """
        db = get_db()
        cur = db.cursor()

        try:
            # 1) rollback status & paidAmount
            sql_update = """
            UPDATE pendaftaran
            SET
                status = 'confirmed',
                paidAmount = 0
            WHERE pendaftaran_id = %s
            """
            cur.execute(sql_update, (pendaftaran_id,))

            # 2) hapus receipt link yang terkait pendaftaran tsb (jika ada)
            sql_delete_link = """
            DELETE FROM pendaftaran_receipt_link
            WHERE pendaftaran_id = %s
            """
            cur.execute(sql_delete_link, (pendaftaran_id,))

            db.commit()
        except Exception:
            db.rollback()
            raise

    # =========================
    # MASTER TARIFF
    # =========================
    @staticmethod
    def get_master_tariff(tariff_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            tariff_code,
            treatment_name,
            price,
            promo_type,
            promo_value,
            promo_start,
            promo_end,
            is_active
        FROM master_tariff
        WHERE id=%s
        AND is_active=1
        LIMIT 1
        """
        cur.execute(sql, (tariff_id,))
        return cur.fetchone()

    @staticmethod
    def list_tariff(search: str = "", limit: int = 5000) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        try:
            limit_i = int(limit)
        except Exception:
            limit_i = 5000
        limit_i = max(1, min(limit_i, 5000))

        sql = """
        SELECT
            id,
            tariff_code,
            treatment_name,
            price,
            promo_type,
            promo_value,
            promo_start,
            promo_end
        FROM master_tariff
        WHERE is_active=1
        """
        params: List[Any] = []

        if search:
            sql += """
            AND (
                tariff_code COLLATE utf8mb4_unicode_ci LIKE %s
                OR treatment_name COLLATE utf8mb4_unicode_ci LIKE %s
            )
            """
            s = f"%{search}%"
            params += [s, s]

        sql += " ORDER BY treatment_name ASC LIMIT %s"
        params.append(limit_i)

        cur.execute(sql, params)
        return cur.fetchall()

    # =========================
    # TREATMENTS
    # =========================
    @staticmethod
    def list_treatments(pendaftaran_id: int):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT *
        FROM pendaftaran_treatment
        WHERE pendaftaran_id=%s
        ORDER BY sort_no, pendaftaran_treatment_id
        """
        cur.execute(sql, (pendaftaran_id,))
        return cur.fetchall()

    @staticmethod
    def insert_treatment(pendaftaran_id: int, row: Dict):
        db = get_db()
        cur = db.cursor()

        sql = """
        INSERT INTO pendaftaran_treatment
        (
            pendaftaran_id,
            tariff_id,
            tariff_code,
            treatment_name_snapshot,
            qty,
            unit_price,
            discount_type,
            discount_value,
            discount_amount,
            promo_code,
            promo_name,
            notes,
            subtotal
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        cur.execute(
            sql,
            (
                pendaftaran_id,
                row["tariff_id"],
                row.get("tariff_code"),
                row["treatment_name_snapshot"],
                row["qty"],
                row["unit_price"],
                row.get("discount_type"),
                row.get("discount_value", 0),
                row.get("discount_amount", 0),
                row.get("promo_code"),
                row.get("promo_name"),
                row.get("notes"),
                row["subtotal"],
            ),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update_treatment(pendaftaran_id: int, detail_id: int, row: Dict):
        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE pendaftaran_treatment
        SET
            qty=%s,
            unit_price=%s,
            discount_type=%s,
            discount_value=%s,
            discount_amount=%s,
            promo_code=%s,
            promo_name=%s,
            notes=%s,
            subtotal=%s
        WHERE pendaftaran_id=%s
          AND pendaftaran_treatment_id=%s
        """

        cur.execute(
            sql,
            (
                row["qty"],
                row["unit_price"],
                row.get("discount_type"),
                row.get("discount_value"),
                row.get("discount_amount"),
                row.get("promo_code"),
                row.get("promo_name"),
                row.get("notes"),
                row["subtotal"],
                pendaftaran_id,
                detail_id,
            ),
        )
        db.commit()

    @staticmethod
    def delete_treatment(pendaftaran_id: int, detail_id: int):
        db = get_db()
        cur = db.cursor()

        sql = """
        DELETE FROM pendaftaran_treatment
        WHERE pendaftaran_id=%s
          AND pendaftaran_treatment_id=%s
        """
        cur.execute(sql, (pendaftaran_id, detail_id))
        db.commit()

    # =========================
    # RECEIPT LINK (PUBLIC)
    # =========================
    @staticmethod
    def _gen_token() -> str:
        # 32 bytes -> 64 hex chars
        return secrets.token_hex(32)

    @staticmethod
    def get_or_create_receipt_token(pendaftaran_id: int) -> str:
        """
        Mengembalikan token receipt untuk pendaftaran_id.
        Jika belum ada, akan dibuat 1x dan disimpan.
        """
        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute(
            "SELECT token FROM pendaftaran_receipt_link WHERE pendaftaran_id=%s LIMIT 1",
            (pendaftaran_id,)
        )
        row = cur.fetchone()
        if row and row.get("token"):
            return row["token"]

        token = PendaftaranRepository._gen_token()

        # insert (unik per pendaftaran)
        cur2 = db.cursor()
        sql = """
        INSERT INTO pendaftaran_receipt_link (pendaftaran_id, token)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE token = VALUES(token)
        """
        cur2.execute(sql, (pendaftaran_id, token))
        db.commit()
        return token

    @staticmethod
    def get_receipt_by_token(token: str) -> Optional[Dict]:
        """
        Ambil data receipt lengkap berdasarkan token publik.
        Output: dict berisi header + patient + treatments + total.
        """
        db = get_db()
        cur = db.cursor(dictionary=True)

        # 1) header + patient + total
        sql_header = """
        SELECT
            p.pendaftaran_id,
            p.patient_code,
            p.tgl_pendaftaran,
            p.anamnesis_umum,
            p.status,
            p.paidAmount,

            pat.full_name,
            pat.phone,
            pat.birth_date,
            pat.address,
            TIMESTAMPDIFF(YEAR, pat.birth_date, DATE(p.tgl_pendaftaran)) AS age_years,

            COALESCE(SUM(pt.subtotal),0) AS total
        FROM pendaftaran_receipt_link rl
        INNER JOIN pendaftaran p
            ON p.pendaftaran_id = rl.pendaftaran_id
        LEFT JOIN patient pat
            ON pat.patient_code COLLATE utf8mb4_unicode_ci
             = p.patient_code   COLLATE utf8mb4_unicode_ci
        LEFT JOIN pendaftaran_treatment pt
            ON pt.pendaftaran_id = p.pendaftaran_id
        WHERE rl.token=%s
        GROUP BY
            p.pendaftaran_id,
            pat.full_name,
            pat.phone,
            pat.birth_date,
            pat.address
        LIMIT 1
        """
        cur.execute(sql_header, (token,))
        header = cur.fetchone()
        if not header:
            return None

        # 2) detail treatments
        cur.execute(
            """
            SELECT
                pendaftaran_treatment_id,
                tariff_code,
                treatment_name_snapshot,
                qty,
                unit_price,
                discount_type,
                discount_value,
                discount_amount,
                subtotal
            FROM pendaftaran_treatment
            WHERE pendaftaran_id=%s
            ORDER BY sort_no, pendaftaran_treatment_id
            """,
            (header["pendaftaran_id"],)
        )
        details = cur.fetchall() or []

        return {"header": header, "details": details}
    
    @staticmethod
    def delete_header(pendaftaran_id: int):
        db = get_db()
        cur = db.cursor()

        try:
            # 1) hapus receipt link jika ada
            cur.execute(
                """
                DELETE FROM pendaftaran_receipt_link
                WHERE pendaftaran_id = %s
                """,
                (pendaftaran_id,)
            )

            # 2) hapus detail treatment
            cur.execute(
                """
                DELETE FROM pendaftaran_treatment
                WHERE pendaftaran_id = %s
                """,
                (pendaftaran_id,)
            )

            # 3) hapus header
            cur.execute(
                """
                DELETE FROM pendaftaran
                WHERE pendaftaran_id = %s
                """,
                (pendaftaran_id,)
            )

            if cur.rowcount == 0:
                raise ValueError("Pendaftaran tidak ditemukan.")

            db.commit()

        except Exception:
            db.rollback()
            raise