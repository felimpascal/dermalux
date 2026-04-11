from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.db import get_db


class TestimoniRepository:
    """
    master_testimoni columns:
      id, name_text, review_date, rating, review_text,
      sort_order, is_active, created_at, updated_at
    """

    @staticmethod
    def _normalize_payload(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
        def has(k: str) -> bool:
            if partial:
                return k in payload
            return k in payload and payload[k] is not None

        out: dict[str, Any] = {}

        required = ["name_text", "review_date", "rating", "review_text", "sort_order", "is_active"]
        if not partial:
            missing = [k for k in required if not has(k)]
            if missing:
                raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if has("name_text"):
            out["name_text"] = str(payload["name_text"]).strip()
            if not out["name_text"]:
                raise ValueError("name_text tidak boleh kosong")

        if has("review_text"):
            out["review_text"] = str(payload["review_text"]).strip()
            if not out["review_text"]:
                raise ValueError("review_text tidak boleh kosong")

        if has("review_date"):
            val = payload["review_date"]
            if isinstance(val, datetime):
                out["review_date"] = val.date()
            elif isinstance(val, date):
                out["review_date"] = val
            else:
                s = str(val).strip()
                if not s:
                    raise ValueError("review_date tidak boleh kosong")
                out["review_date"] = s

        if has("rating"):
            try:
                out["rating"] = int(payload["rating"])
            except Exception:
                raise ValueError("rating harus angka")
            if out["rating"] < 1 or out["rating"] > 5:
                raise ValueError("rating harus antara 1 sampai 5")

        if has("sort_order"):
            try:
                out["sort_order"] = int(payload["sort_order"])
            except Exception:
                raise ValueError("sort_order harus angka")

        if has("is_active"):
            try:
                out["is_active"] = 1 if int(payload["is_active"]) else 0
            except Exception:
                raise ValueError("is_active harus 0 atau 1")

        return out

    @staticmethod
    def list_testimoni(
        search: str | None = None,
        active_only: bool = False,
        limit: int = 500,
        offset: int = 0,
    ):
        db = get_db()
        cur = db.cursor(dictionary=True)

        where = []
        params: dict[str, Any] = {}

        if search:
            where.append("(name_text LIKE %(q)s OR review_text LIKE %(q)s)")
            params["q"] = f"%{search.strip()}%"

        if active_only:
            where.append("is_active = 1")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sql = f"""
        SELECT
            id,
            name_text,
            review_date,
            rating,
            review_text,
            sort_order,
            is_active,
            created_at,
            updated_at
        FROM master_testimoni
        {where_sql}
        ORDER BY sort_order ASC, review_date DESC, id DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """

        params["limit"] = int(limit)
        params["offset"] = int(offset)

        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def list_public(limit: int = 20):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            name_text,
            review_date,
            rating,
            review_text,
            sort_order
        FROM master_testimoni
        WHERE is_active = 1
        ORDER BY RAND()
        LIMIT %s
        """
        cur.execute(sql, (max(1, int(limit)),))
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_by_id(testimoni_id: int):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            name_text,
            review_date,
            rating,
            review_text,
            sort_order,
            is_active,
            created_at,
            updated_at
        FROM master_testimoni
        WHERE id = %s
        LIMIT 1
        """
        cur.execute(sql, (testimoni_id,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def insert(payload: dict):
        db = get_db()

        data = TestimoniRepository._normalize_payload(payload, partial=False)

        sql = """
        INSERT INTO master_testimoni
        (
            name_text,
            review_date,
            rating,
            review_text,
            sort_order,
            is_active
        )
        VALUES
        (
            %(name_text)s,
            %(review_date)s,
            %(rating)s,
            %(review_text)s,
            %(sort_order)s,
            %(is_active)s
        )
        """

        cur = db.cursor()
        cur.execute(sql, data)
        db.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id

    @staticmethod
    def update(testimoni_id: int, payload: dict):
        if not payload:
            return 0

        db = get_db()
        data = TestimoniRepository._normalize_payload(payload, partial=True)

        if not data:
            return 0

        allowed = {
            "name_text",
            "review_date",
            "rating",
            "review_text",
            "sort_order",
            "is_active",
        }

        sets = []
        params: dict[str, Any] = {}

        for k, v in data.items():
            if k not in allowed:
                continue
            sets.append(f"{k}=%({k})s")
            params[k] = v

        if not sets:
            return 0

        params["id"] = testimoni_id

        sql = f"""
        UPDATE master_testimoni
        SET {", ".join(sets)}
        WHERE id=%(id)s
        """

        cur = db.cursor()
        cur.execute(sql, params)
        db.commit()
        affected = cur.rowcount
        cur.close()
        return affected

    @staticmethod
    def set_active(testimoni_id: int, is_active: int):
        db = get_db()
        cur = db.cursor()

        cur.execute(
            "UPDATE master_testimoni SET is_active=%s WHERE id=%s",
            (1 if int(is_active) else 0, testimoni_id),
        )
        db.commit()
        affected = cur.rowcount
        cur.close()
        return affected