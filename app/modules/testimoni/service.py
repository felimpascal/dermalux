from __future__ import annotations

from datetime import date
from typing import Any

from app.common.errors import AppError
from .repository import TestimoniRepository


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


def _parse_rating(x: Any, field_name: str = "Rating") -> int:
    try:
        v = int(str(x).strip())
        if v < 1 or v > 5:
            raise ValueError()
        return v
    except Exception:
        raise AppError(f"{field_name} harus berupa angka 1 sampai 5.", 400)


def _parse_date(d: Any):
    if d is None or str(d).strip() == "":
        raise AppError("Tanggal review wajib diisi.", 400)

    s = str(d).strip()
    try:
        y, m, dd = s.split("-")
        return date(int(y), int(m), int(dd))
    except Exception:
        raise AppError("Format tanggal tidak valid (harus YYYY-MM-DD).", 400)


class TestimoniService:

    @staticmethod
    def normalize_and_validate_create(data: dict) -> dict:
        name_text = _clean_text(data.get("name_text"))
        review_text = _clean_text(data.get("review_text"))

        if not name_text:
            raise AppError("Nama wajib diisi.", 400)

        if not review_text:
            raise AppError("Review wajib diisi.", 400)

        review_date = _parse_date(data.get("review_date"))
        rating = _parse_rating(data.get("rating"), "Rating")
        sort_order = _parse_sort_order(data.get("sort_order"), "Nomor urut")
        is_active = _to_int01(data.get("is_active"), default=1)

        payload = {
            "name_text": name_text,
            "review_date": review_date,
            "rating": rating,
            "review_text": review_text,
            "sort_order": sort_order,
            "is_active": is_active,
        }
        return payload

    @staticmethod
    def normalize_and_validate_update(data: dict, testimoni_id: int) -> dict:
        row = TestimoniRepository.get_by_id(testimoni_id)
        if not row:
            raise AppError("Data testimoni tidak ditemukan.", 404)

        payload: dict[str, Any] = {}

        if "name_text" in data:
            name_text = _clean_text(data.get("name_text"))
            if not name_text:
                raise AppError("Nama wajib diisi.", 400)
            payload["name_text"] = name_text

        if "review_text" in data:
            review_text = _clean_text(data.get("review_text"))
            if not review_text:
                raise AppError("Review wajib diisi.", 400)
            payload["review_text"] = review_text

        if "review_date" in data:
            payload["review_date"] = _parse_date(data.get("review_date"))

        if "rating" in data:
            payload["rating"] = _parse_rating(data.get("rating"), "Rating")

        if "sort_order" in data:
            payload["sort_order"] = _parse_sort_order(data.get("sort_order"), "Nomor urut")

        if "is_active" in data:
            payload["is_active"] = _to_int01(
                data.get("is_active"),
                default=int(row.get("is_active", 1))
            )

        return payload

    @staticmethod
    def create(data: dict) -> int:
        payload = TestimoniService.normalize_and_validate_create(data)
        return TestimoniRepository.insert(payload)

    @staticmethod
    def edit(testimoni_id: int, data: dict):
        payload = TestimoniService.normalize_and_validate_update(data, testimoni_id)
        affected = TestimoniRepository.update(testimoni_id, payload)
        if affected <= 0:
            raise AppError("Data testimoni tidak berubah.", 400)

    @staticmethod
    def disable(testimoni_id: int):
        affected = TestimoniRepository.set_active(testimoni_id, 0)
        if affected <= 0:
            raise AppError("Data testimoni tidak ditemukan.", 404)

    @staticmethod
    def enable(testimoni_id: int):
        affected = TestimoniRepository.set_active(testimoni_id, 1)
        if affected <= 0:
            raise AppError("Data testimoni tidak ditemukan.", 404)