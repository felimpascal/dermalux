from __future__ import annotations

from typing import Any

from app.db import get_db


class TeamRepository:
    """
    master_team columns:
      id, name, position, photo_path, photo_original_name,
      sort_order, is_active, created_at, updated_at
    """

    @staticmethod
    def _normalize_payload(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
        """
        Normalize and validate payload.
        If partial=True, field yang dikirim boleh di-set ke NULL
        untuk kolom yang memang nullable seperti photo_path/photo_original_name.
        """
        def has(k: str) -> bool:
            if partial:
                return k in payload
            return k in payload and payload[k] is not None

        out: dict[str, Any] = {}

        required = ["name", "position", "sort_order", "is_active"]
        if not partial:
            missing = [k for k in required if not has(k)]
            if missing:
                raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if has("name"):
            out["name"] = str(payload["name"]).strip()
            if not out["name"]:
                raise ValueError("name tidak boleh kosong")

        if has("position"):
            out["position"] = str(payload["position"]).strip()
            if not out["position"]:
                raise ValueError("position tidak boleh kosong")

        if has("photo_path"):
            out["photo_path"] = (
                str(payload["photo_path"]).strip()
                if payload["photo_path"] is not None
                else None
            ) or None

        if has("photo_original_name"):
            out["photo_original_name"] = (
                str(payload["photo_original_name"]).strip()
                if payload["photo_original_name"] is not None
                else None
            ) or None

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
    def list_teams(
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
            where.append("(name LIKE %(q)s OR position LIKE %(q)s)")
            params["q"] = f"%{search.strip()}%"

        if active_only:
            where.append("is_active = 1")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sql = f"""
        SELECT
            id,
            name,
            position,
            photo_path,
            photo_original_name,
            sort_order,
            is_active,
            created_at,
            updated_at
        FROM master_team
        {where_sql}
        ORDER BY sort_order ASC, id ASC
        LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = int(limit)
        params["offset"] = int(offset)

        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def list_public(limit: int = 100):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            name,
            position,
            photo_path,
            photo_original_name,
            sort_order
        FROM master_team
        WHERE is_active = 1
        ORDER BY sort_order ASC, id ASC
        LIMIT %s
        """
        cur.execute(sql, (int(limit),))
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_by_id(team_id: int):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            name,
            position,
            photo_path,
            photo_original_name,
            sort_order,
            is_active,
            created_at,
            updated_at
        FROM master_team
        WHERE id = %s
        LIMIT 1
        """
        cur.execute(sql, (team_id,))
        row = cur.fetchone()
        cur.close()
        return row

    @staticmethod
    def insert(payload: dict):
        db = get_db()

        data = TeamRepository._normalize_payload(payload, partial=False)

        data.setdefault("photo_path", None)
        data.setdefault("photo_original_name", None)

        sql = """
        INSERT INTO master_team
        (
            name,
            position,
            photo_path,
            photo_original_name,
            sort_order,
            is_active
        )
        VALUES
        (
            %(name)s,
            %(position)s,
            %(photo_path)s,
            %(photo_original_name)s,
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
    def update(team_id: int, payload: dict):
        """
        Partial update.
        Hanya field yang dikirim yang diupdate.
        """
        if not payload:
            return 0

        db = get_db()
        data = TeamRepository._normalize_payload(payload, partial=True)

        if not data:
            return 0

        allowed = {
            "name",
            "position",
            "photo_path",
            "photo_original_name",
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

        params["id"] = team_id

        sql = f"""
        UPDATE master_team
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
    def set_active(team_id: int, is_active: int):
        db = get_db()
        cur = db.cursor()

        cur.execute(
            "UPDATE master_team SET is_active=%s WHERE id=%s",
            (1 if int(is_active) else 0, team_id),
        )
        db.commit()
        affected = cur.rowcount
        cur.close()
        return affected
    
    @staticmethod
    def list_active_ordered(limit: int = 100):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            name,
            position,
            photo_path,
            photo_original_name,
            sort_order
        FROM master_team
        WHERE is_active = 1
        ORDER BY sort_order ASC, id ASC
        LIMIT %s
        """
        cur.execute(sql, (int(limit),))
        rows = cur.fetchall()
        cur.close()
        return rows