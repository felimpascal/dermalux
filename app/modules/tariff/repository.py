from __future__ import annotations

from typing import Any, Optional

from app.db import get_db


class TariffRepository:
    """
    master_tariff columns assumed:
      id, tariff_code, category_id, treatment_name,
      photo_path, photo_original_name,
      price, promo_type, promo_value, promo_start, promo_end, promo_category,
      is_active, created_at, updated_at

    master_tariff_category columns:
      id, category_code, category_name, is_active, created_at, updated_at
    """

    # ----- helpers -----

    @staticmethod
    def _compute_promo_sql(alias: str = "t"):
        """
        Returns tuple (promo_is_active_sql, promo_price_sql)
        promo_price is computed ONLY when promo is active; else equals price.
        Clamps negative promo result to 0.
        """
        promo_is_active = f"""
        (
            {alias}.promo_type <> 'none'
            AND {alias}.promo_start IS NOT NULL AND {alias}.promo_end IS NOT NULL
            AND CURDATE() BETWEEN {alias}.promo_start AND {alias}.promo_end
        )
        """

        promo_price = f"""
        CASE
            WHEN {promo_is_active} THEN
                GREATEST(
                    CASE
                        WHEN {alias}.promo_type = 'percent' THEN ROUND({alias}.price - ({alias}.price * {alias}.promo_value / 100), 2)
                        WHEN {alias}.promo_type = 'amount'  THEN ROUND({alias}.price - {alias}.promo_value, 2)
                        ELSE {alias}.price
                    END
                , 0)
            ELSE {alias}.price
        END
        """

        return promo_is_active, promo_price

    @staticmethod
    def _normalize_payload(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
        def has(k: str) -> bool:
            if partial:
                return k in payload
            return k in payload and payload[k] is not None

        out: dict[str, Any] = {}

        required = ["tariff_code", "treatment_name", "price", "is_active"]
        if not partial:
            missing = [k for k in required if not has(k)]
            if missing:
                raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if has("tariff_code"):
            out["tariff_code"] = str(payload["tariff_code"]).strip()
            if not out["tariff_code"]:
                raise ValueError("tariff_code tidak boleh kosong")

        if has("treatment_name"):
            out["treatment_name"] = str(payload["treatment_name"]).strip()
            if not out["treatment_name"]:
                raise ValueError("treatment_name tidak boleh kosong")

        if has("photo_path"):
            out["photo_path"] = (
                str(payload["photo_path"]).strip() if payload["photo_path"] is not None else None
            ) or None

        if has("photo_original_name"):
            out["photo_original_name"] = (
                str(payload["photo_original_name"]).strip() if payload["photo_original_name"] is not None else None
            ) or None

        if has("category_id"):
            if payload["category_id"] is None or str(payload["category_id"]).strip() == "":
                out["category_id"] = None
            else:
                try:
                    out["category_id"] = int(payload["category_id"])
                except Exception:
                    raise ValueError("category_id harus angka")

        if has("category_code"):
            cc = str(payload["category_code"]).strip().upper() if payload["category_code"] is not None else ""
            if cc:
                out["category_code"] = cc

        if has("price"):
            out["price"] = payload["price"]

        if has("is_active"):
            out["is_active"] = 1 if int(payload["is_active"]) else 0

        promo_type = payload.get("promo_type", None)
        if promo_type is not None:
            promo_type = str(promo_type).strip().lower()
            if promo_type not in ("none", "percent", "amount"):
                raise ValueError("promo_type harus salah satu: none|percent|amount")
            out["promo_type"] = promo_type

        if "promo_value" in payload:
            out["promo_value"] = payload["promo_value"] if payload["promo_value"] is not None else 0

        if "promo_start" in payload:
            out["promo_start"] = payload.get("promo_start")

        if "promo_end" in payload:
            out["promo_end"] = payload.get("promo_end")

        if has("promo_category"):
            out["promo_category"] = (
                str(payload["promo_category"]).strip()
                if payload["promo_category"] is not None
                else None
            ) or None

        if out.get("promo_type") == "none":
            out.setdefault("promo_value", 0)
            out.setdefault("promo_start", None)
            out.setdefault("promo_end", None)
            out.setdefault("promo_category", None)

        if out.get("promo_type") in ("percent", "amount"):
            if (not partial) or ("promo_start" in out or "promo_end" in out):
                if out.get("promo_start") is None or out.get("promo_end") is None:
                    raise ValueError("promo_start dan promo_end wajib diisi jika promo_type bukan 'none'")

        return out

    @staticmethod
    def _get_category_id_by_code(category_code: str) -> Optional[int]:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id
            FROM master_tariff_category
            WHERE category_code = %s
            LIMIT 1
            """,
            (category_code.strip().upper(),),
        )
        row = cur.fetchone()
        cur.close()
        return int(row["id"]) if row else None

    # ----- queries -----

    @staticmethod
    def list_tariffs(
        search: str | None = None,
        active_only: bool = False,
        category_id: int | None = None,
        category_code: str | None = None,
        promo_only_today: bool = False,
        limit: int = 500,
        offset: int = 0,
    ):
        db = get_db()
        cur = db.cursor(dictionary=True)

        promo_is_active_sql, promo_price_sql = TariffRepository._compute_promo_sql("t")

        where = []
        params: dict[str, Any] = {}

        if search:
            where.append("(t.tariff_code LIKE %(q)s OR t.treatment_name LIKE %(q)s OR t.promo_category LIKE %(q)s)")
            params["q"] = f"%{search.strip()}%"

        if active_only:
            where.append("t.is_active = 1")

        if promo_only_today:
            where.append(promo_is_active_sql)

        if category_id is not None:
            where.append("t.category_id = %(cat_id)s")
            params["cat_id"] = int(category_id)
        elif category_code:
            where.append("c.category_code = %(cat_code)s")
            params["cat_code"] = category_code.strip().upper()

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sql = f"""
        SELECT
            t.id,
            t.tariff_code,
            t.category_id,
            c.category_code,
            c.category_name,
            t.treatment_name,
            t.photo_path,
            t.photo_original_name,
            t.price,
            t.promo_type,
            t.promo_value,
            t.promo_start,
            t.promo_end,
            t.promo_category,
            t.is_active,
            t.created_at,
            t.updated_at,
            CASE WHEN {promo_is_active_sql} THEN 1 ELSE 0 END AS promo_is_active,
            {promo_price_sql} AS promo_price,
            {promo_price_sql} AS final_price
        FROM master_tariff t
        LEFT JOIN master_tariff_category c
            ON c.id = t.category_id
        {where_sql}
        ORDER BY t.is_active DESC, c.category_name ASC, t.treatment_name ASC
        LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = int(limit)
        params["offset"] = int(offset)

        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_by_id(tariff_id: int):
        db = get_db()
        cur = db.cursor(dictionary=True)

        promo_is_active_sql, promo_price_sql = TariffRepository._compute_promo_sql("t")

        sql = f"""
        SELECT
            t.id,
            t.tariff_code,
            t.category_id,
            t.treatment_name,
            t.photo_path,
            t.photo_original_name,
            t.price,
            t.promo_type,
            t.promo_value,
            t.promo_start,
            t.promo_end,
            t.promo_category,
            t.is_active,
            t.created_at,
            t.updated_at,
            c.category_code,
            c.category_name,
            CASE WHEN {promo_is_active_sql} THEN 1 ELSE 0 END AS promo_is_active,
            {promo_price_sql} AS promo_price,
            {promo_price_sql} AS final_price
        FROM master_tariff t
        LEFT JOIN master_tariff_category c
            ON c.id = t.category_id
        WHERE t.id=%s
        """
        cur.execute(sql, (tariff_id,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def get_by_code(tariff_code: str):
        db = get_db()
        cur = db.cursor(dictionary=True)

        promo_is_active_sql, promo_price_sql = TariffRepository._compute_promo_sql("t")

        sql = f"""
        SELECT
            t.id,
            t.tariff_code,
            t.category_id,
            t.treatment_name,
            t.photo_path,
            t.photo_original_name,
            t.price,
            t.promo_type,
            t.promo_value,
            t.promo_start,
            t.promo_end,
            t.promo_category,
            t.is_active,
            t.created_at,
            t.updated_at,
            c.category_code,
            c.category_name,
            CASE WHEN {promo_is_active_sql} THEN 1 ELSE 0 END AS promo_is_active,
            {promo_price_sql} AS promo_price,
            {promo_price_sql} AS final_price
        FROM master_tariff t
        LEFT JOIN master_tariff_category c
            ON c.id = t.category_id
        WHERE t.tariff_code=%s
        LIMIT 1
        """
        cur.execute(sql, (tariff_code.strip(),))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def insert(payload: dict):
        db = get_db()

        data = TariffRepository._normalize_payload(payload, partial=False)

        if "category_id" not in data and "category_code" in data:
            cid = TariffRepository._get_category_id_by_code(data["category_code"])
            if cid is None:
                raise ValueError("category_code tidak ditemukan di master_tariff_category")
            data["category_id"] = cid

        cols = [
            "tariff_code",
            "category_id",
            "treatment_name",
            "photo_path",
            "photo_original_name",
            "price",
            "promo_type",
            "promo_value",
            "promo_start",
            "promo_end",
            "promo_category",
            "is_active",
        ]
        vals = [
            "%(tariff_code)s",
            "%(category_id)s",
            "%(treatment_name)s",
            "%(photo_path)s",
            "%(photo_original_name)s",
            "%(price)s",
            "%(promo_type)s",
            "%(promo_value)s",
            "%(promo_start)s",
            "%(promo_end)s",
            "%(promo_category)s",
            "%(is_active)s",
        ]

        data.setdefault("promo_type", "none")
        data.setdefault("promo_value", 0)
        data.setdefault("promo_start", None)
        data.setdefault("promo_end", None)
        data.setdefault("promo_category", None)

        data.setdefault("photo_path", None)
        data.setdefault("photo_original_name", None)

        data.setdefault("category_id", None)

        sql = f"""
        INSERT INTO master_tariff
        ({", ".join(cols)})
        VALUES
        ({", ".join(vals)})
        """
        cur = db.cursor()
        cur.execute(sql, data)
        db.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id

    @staticmethod
    def update(tariff_id: int, payload: dict):
        """
        Partial update: only keys present in payload will be updated.
        """
        if not payload:
            return 0

        db = get_db()

        data = TariffRepository._normalize_payload(payload, partial=True)
        if not data:
            return 0

        if "category_code" in data and "category_id" not in data:
            cid = TariffRepository._get_category_id_by_code(data["category_code"])
            if cid is None:
                raise ValueError("category_code tidak ditemukan di master_tariff_category")
            data["category_id"] = cid

        allowed = {
            "tariff_code",
            "category_id",
            "treatment_name",
            "photo_path",
            "photo_original_name",
            "price",
            "promo_type",
            "promo_value",
            "promo_start",
            "promo_end",
            "promo_category",
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

        params["id"] = tariff_id

        sql = f"""
        UPDATE master_tariff
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
    def set_active(tariff_id: int, is_active: int):
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "UPDATE master_tariff SET is_active=%s WHERE id=%s",
            (1 if int(is_active) else 0, tariff_id),
        )
        db.commit()
        affected = cur.rowcount
        cur.close()
        return affected

    @staticmethod
    def list_today_active_promos(limit: int = 500, offset: int = 0):
        db = get_db()
        cur = db.cursor(dictionary=True)

        promo_is_active_sql, promo_price_sql = TariffRepository._compute_promo_sql("t")

        sql = f"""
        SELECT
            t.id,
            t.tariff_code,
            t.category_id,
            c.category_code,
            c.category_name,
            t.treatment_name,
            t.photo_path,
            t.photo_original_name,
            t.price,
            t.promo_type,
            t.promo_value,
            t.promo_start,
            t.promo_end,
            t.promo_category,
            {promo_price_sql} AS promo_price
        FROM master_tariff t
        LEFT JOIN master_tariff_category c
            ON c.id = t.category_id
        WHERE
            t.is_active = 1
            AND {promo_is_active_sql}
        ORDER BY t.promo_end ASC, t.treatment_name ASC
        LIMIT %s OFFSET %s
        """
        cur.execute(sql, (int(limit), int(offset)))
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def clear_promo(tariff_id: int):
        db = get_db()
        cur = db.cursor()
        sql = """
        UPDATE master_tariff
        SET
            promo_type='none',
            promo_value=0,
            promo_start=NULL,
            promo_end=NULL,
            promo_category=NULL
        WHERE id=%s
        """
        cur.execute(sql, (tariff_id,))
        db.commit()
        affected = cur.rowcount
        cur.close()
        return affected

    @staticmethod
    def set_promo(
        tariff_id: int,
        promo_type: str,
        promo_value,
        promo_start,
        promo_end,
        promo_category=None,
    ):
        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE master_tariff
        SET
            promo_type=%s,
            promo_value=%s,
            promo_start=%s,
            promo_end=%s,
            promo_category=%s
        WHERE id=%s
        """
        cur.execute(
            sql,
            (
                promo_type,
                promo_value,
                promo_start,
                promo_end,
                (str(promo_category).strip() if promo_category is not None else None) or None,
                tariff_id,
            ),
        )
        db.commit()
        affected = cur.rowcount
        cur.close()
        return affected

    @staticmethod
    def list_categories(active_only: bool = True):
        db = get_db()
        cur = db.cursor(dictionary=True)

        where = ""
        params = ()
        if active_only:
            where = "WHERE is_active = 1"

        sql = f"""
        SELECT id, category_code, category_name, is_active
        FROM master_tariff_category
        {where}
        ORDER BY category_name ASC
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def list_distinct_promo_categories(active_only: bool = False):
        db = get_db()
        cur = db.cursor(dictionary=True)

        where = [
            "promo_category IS NOT NULL",
            "TRIM(promo_category) <> ''",
        ]

        if active_only:
            promo_is_active_sql, _ = TariffRepository._compute_promo_sql("t")
            where.append("t.is_active = 1")
            where.append(promo_is_active_sql)

        sql = f"""
        SELECT DISTINCT t.promo_category
        FROM master_tariff t
        WHERE {" AND ".join(where)}
        ORDER BY t.promo_category ASC
        """
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        return rows