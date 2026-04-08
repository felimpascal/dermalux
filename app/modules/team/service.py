from __future__ import annotations

from typing import Any

from app.common.errors import AppError
from .repository import TeamRepository


def _clean_text(x: Any) -> str:
    return (str(x) if x is not None else "").strip()


def _to_int01(x: Any, default: int = 1) -> int:
    if x is None or str(x).strip() == "":
        return 1 if default else 0
    try:
        v = int(x)
    except Exception:
        v = default
    return 1 if v == 1 else 0


def _parse_sort_order(x: Any, field_name: str = "Nomor urut") -> int:
    if x is None or str(x).strip() == "":
        return 0
    try:
        v = int(str(x).strip())
        if v < 0:
            raise ValueError()
        return v
    except Exception:
        raise AppError(f"{field_name} harus berupa angka 0 atau lebih.", 400)


class TeamService:

    @staticmethod
    def normalize_and_validate_create(data: dict) -> dict:
        """
        Create membutuhkan:
        - name (wajib)
        - position (wajib)
        - sort_order (opsional, default 0)
        - is_active (opsional, default 1)
        - photo_path / photo_original_name (opsional)
        """
        name = _clean_text(data.get("name"))
        position = _clean_text(data.get("position"))
        photo_path = _clean_text(data.get("photo_path")) or None
        photo_original_name = _clean_text(data.get("photo_original_name")) or None

        if not name:
            raise AppError("Nama tim wajib diisi.", 400)

        if not position:
            raise AppError("Jabatan / spesialis wajib diisi.", 400)

        sort_order = _parse_sort_order(data.get("sort_order"), "Nomor urut")
        is_active = _to_int01(data.get("is_active"), default=1)

        payload = {
            "name": name,
            "position": position,
            "photo_path": photo_path,
            "photo_original_name": photo_original_name,
            "sort_order": sort_order,
            "is_active": is_active,
        }
        return payload

    @staticmethod
    def normalize_and_validate_update(data: dict, team_id: int) -> dict:
        """
        Update bersifat partial (PATCH):
        - hanya field yang dikirim yang diubah
        - photo_path dan photo_original_name boleh di-set None
        """
        row = TeamRepository.get_by_id(team_id)
        if not row:
            raise AppError("Data tim tidak ditemukan.", 404)

        payload: dict[str, Any] = {}

        if "name" in data:
            name = _clean_text(data.get("name"))
            if not name:
                raise AppError("Nama tim wajib diisi.", 400)
            payload["name"] = name

        if "position" in data:
            position = _clean_text(data.get("position"))
            if not position:
                raise AppError("Jabatan / spesialis wajib diisi.", 400)
            payload["position"] = position

        if "photo_path" in data:
            payload["photo_path"] = _clean_text(data.get("photo_path")) or None

        if "photo_original_name" in data:
            payload["photo_original_name"] = _clean_text(data.get("photo_original_name")) or None

        if "sort_order" in data:
            payload["sort_order"] = _parse_sort_order(data.get("sort_order"), "Nomor urut")

        if "is_active" in data:
            payload["is_active"] = _to_int01(
                data.get("is_active"),
                default=int(row.get("is_active", 1))
            )

        return payload

    # ----- actions -----

    @staticmethod
    def create(data: dict) -> int:
        payload = TeamService.normalize_and_validate_create(data)
        return TeamRepository.insert(payload)

    @staticmethod
    def edit(team_id: int, data: dict):
        payload = TeamService.normalize_and_validate_update(data, team_id)
        affected = TeamRepository.update(team_id, payload)
        if affected <= 0:
            raise AppError("Data tim tidak berubah.", 400)

    @staticmethod
    def disable(team_id: int):
        affected = TeamRepository.set_active(team_id, 0)
        if affected <= 0:
            raise AppError("Data tim tidak ditemukan.", 404)

    @staticmethod
    def enable(team_id: int):
        affected = TeamRepository.set_active(team_id, 1)
        if affected <= 0:
            raise AppError("Data tim tidak ditemukan.", 404)