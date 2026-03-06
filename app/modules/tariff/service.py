from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.common.errors import AppError
from .repository import TariffRepository


ALLOWED_PROMO_TYPES = {"none", "percent", "amount"}


def _parse_date(d: str | None):
    if not d or str(d).strip() == "":
        return None
    s = str(d).strip()
    try:
        # input type="date" => YYYY-MM-DD
        y, m, dd = s.split("-")
        return date(int(y), int(m), int(dd))
    except Exception:
        raise AppError("Format tanggal tidak valid (harus YYYY-MM-DD).", 400)


def _parse_money(x: Any, field_name: str) -> Decimal:
    """
    Parse angka uang secara aman.
    Mendukung:
      - "79900"
      - "79,900"
      - 79900
      - "" / None -> 0
    """
    if x is None:
        return Decimal("0")

    s = str(x).strip()
    if s == "":
        return Decimal("0")

    s = s.replace(",", "")

    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise AppError(f"Format angka tidak valid untuk {field_name}.", 400)


def _to_int01(x: Any, default: int = 1) -> int:
    if x is None or str(x).strip() == "":
        return 1 if default else 0
    try:
        v = int(x)
    except Exception:
        v = default
    return 1 if v == 1 else 0


def _clean_text(x: Any) -> str:
    return (str(x) if x is not None else "").strip()


def _parse_int_optional(x: Any, field_name: str) -> int | None:
    if x is None or str(x).strip() == "":
        return None
    try:
        v = int(str(x).strip())
        if v <= 0:
            raise ValueError()
        return v
    except Exception:
        raise AppError(f"{field_name} harus berupa angka yang valid.", 400)


class TariffService:

    @staticmethod
    def normalize_and_validate_create(data: dict) -> dict:
        """
        Create membutuhkan field wajib (tariff_code, treatment_name, price).
        category_id: opsional, tapi jika diisi harus valid integer.
        """
        tariff_code = _clean_text(data.get("tariff_code"))
        treatment_name = _clean_text(data.get("treatment_name"))

        if not tariff_code:
            raise AppError("Kode tarif wajib diisi.", 400)
        if not treatment_name:
            raise AppError("Nama treatment wajib diisi.", 400)

        # category (opsional)
        category_id = _parse_int_optional(data.get("category_id"), "Kategori")

        price = _parse_money(data.get("price"), "harga")
        if price < 0:
            raise AppError("Harga tidak boleh negatif.", 400)

        promo_type = _clean_text(data.get("promo_type") or "none").lower()
        if promo_type not in ALLOWED_PROMO_TYPES:
            raise AppError("promo_type tidak valid.", 400)

        promo_value = _parse_money(data.get("promo_value"), "diskon/promo")
        promo_start = _parse_date(data.get("promo_start"))
        promo_end = _parse_date(data.get("promo_end"))

        is_active = _to_int01(data.get("is_active"), default=1)

        # Unique code check
        existing = TariffRepository.get_by_code(tariff_code)
        if existing:
            raise AppError("Kode tarif sudah digunakan.", 400)

        # Promo rules
        promo_type, promo_value, promo_start, promo_end = TariffService._validate_promo(
            price=price,
            promo_type=promo_type,
            promo_value=promo_value,
            promo_start=promo_start,
            promo_end=promo_end,
        )

        payload = {
            "tariff_code": tariff_code,
            "treatment_name": treatment_name,
            "category_id": category_id,  # boleh None
            "price": float(price.quantize(Decimal("0.01"))),
            "promo_type": promo_type,
            "promo_value": float(promo_value.quantize(Decimal("0.01"))),
            "promo_start": promo_start,
            "promo_end": promo_end,
            "is_active": is_active,
        }
        return payload

    @staticmethod
    def normalize_and_validate_update(data: dict, tariff_id: int) -> dict:
        """
        Update bersifat partial (PATCH):
        - hanya field yang dikirim yang diubah
        - validasi promo mempertimbangkan kondisi existing jika promo field disentuh
        """
        row = TariffRepository.get_by_id(tariff_id)
        if not row:
            raise AppError("Tarif tidak ditemukan.", 404)

        payload: dict[str, Any] = {}

        # ---- text fields (partial) ----
        if "tariff_code" in data:
            tariff_code = _clean_text(data.get("tariff_code"))
            if not tariff_code:
                raise AppError("Kode tarif wajib diisi.", 400)

            existing = TariffRepository.get_by_code(tariff_code)
            if existing and int(existing["id"]) != int(tariff_id):
                raise AppError("Kode tarif sudah digunakan.", 400)

            payload["tariff_code"] = tariff_code

        if "treatment_name" in data:
            treatment_name = _clean_text(data.get("treatment_name"))
            if not treatment_name:
                raise AppError("Nama treatment wajib diisi.", 400)
            payload["treatment_name"] = treatment_name

        # ---- category (partial) ----
        # NOTE: form select biasanya mengirim "" jika tidak dipilih
        if "category_id" in data:
            payload["category_id"] = _parse_int_optional(data.get("category_id"), "Kategori")

        # ---- numeric fields (partial) ----
        if "price" in data:
            price = _parse_money(data.get("price"), "harga")
            if price < 0:
                raise AppError("Harga tidak boleh negatif.", 400)
            payload["price"] = float(price.quantize(Decimal("0.01")))
        else:
            price = Decimal(str(row["price"]))  # untuk validasi promo amount

        if "is_active" in data:
            payload["is_active"] = _to_int01(data.get("is_active"), default=int(row.get("is_active", 1)))

        # ---- promo fields ----
        promo_touched = any(k in data for k in ("promo_type", "promo_value", "promo_start", "promo_end"))

        if promo_touched:
            promo_type = _clean_text(data.get("promo_type", row.get("promo_type", "none"))).lower()
            if promo_type not in ALLOWED_PROMO_TYPES:
                raise AppError("promo_type tidak valid.", 400)

            promo_value = (
                _parse_money(data.get("promo_value"), "diskon/promo")
                if "promo_value" in data
                else Decimal(str(row.get("promo_value", 0) or 0))
            )

            promo_start = _parse_date(data.get("promo_start")) if "promo_start" in data else row.get("promo_start")
            promo_end = _parse_date(data.get("promo_end")) if "promo_end" in data else row.get("promo_end")

            # row promo_start/promo_end bisa date/datetime
            if promo_start and hasattr(promo_start, "date") and not isinstance(promo_start, date):
                promo_start = promo_start.date()
            if promo_end and hasattr(promo_end, "date") and not isinstance(promo_end, date):
                promo_end = promo_end.date()

            promo_type, promo_value, promo_start, promo_end = TariffService._validate_promo(
                price=price,
                promo_type=promo_type,
                promo_value=promo_value,
                promo_start=promo_start,
                promo_end=promo_end,
            )

            payload["promo_type"] = promo_type
            payload["promo_value"] = float(promo_value.quantize(Decimal("0.01")))
            payload["promo_start"] = promo_start
            payload["promo_end"] = promo_end

        return payload

    @staticmethod
    def _validate_promo(
        *,
        price: Decimal,
        promo_type: str,
        promo_value: Decimal,
        promo_start: date | None,
        promo_end: date | None,
    ):
        if promo_type == "none":
            return "none", Decimal("0"), None, None

        if promo_value <= 0:
            raise AppError("Nilai diskon/promo harus > 0 jika promo aktif.", 400)
        if not promo_start or not promo_end:
            raise AppError("Start date dan end date promo wajib diisi jika promo aktif.", 400)
        if promo_start > promo_end:
            raise AppError("Start date promo tidak boleh melebihi end date promo.", 400)

        if promo_type == "percent":
            if promo_value > 100:
                raise AppError("Diskon persen tidak boleh > 100.", 400)

        if promo_type == "amount":
            if promo_value > price:
                raise AppError("Diskon nominal tidak boleh melebihi harga.", 400)

        return promo_type, promo_value, promo_start, promo_end

    # ----- actions -----

    @staticmethod
    def create(data: dict) -> int:
        payload = TariffService.normalize_and_validate_create(data)
        return TariffRepository.insert(payload)

    @staticmethod
    def edit(tariff_id: int, data: dict):
        payload = TariffService.normalize_and_validate_update(data, tariff_id)
        affected = TariffRepository.update(tariff_id, payload)
        if affected <= 0:
            raise AppError("Data tarif tidak berubah.", 400)

    @staticmethod
    def disable(tariff_id: int):
        affected = TariffRepository.set_active(tariff_id, 0)
        if affected <= 0:
            raise AppError("Data tarif tidak ditemukan.", 404)

    @staticmethod
    def enable(tariff_id: int):
        affected = TariffRepository.set_active(tariff_id, 1)
        if affected <= 0:
            raise AppError("Data tarif tidak ditemukan.", 404)

    @staticmethod
    def disable_promo(tariff_id: int):
        row = TariffRepository.get_by_id(tariff_id)
        if not row:
            raise AppError("Tarif tidak ditemukan.", 404)

        affected = TariffRepository.clear_promo(tariff_id)
        if affected <= 0:
            raise AppError("Gagal menonaktifkan promo.", 400)

    @staticmethod
    def set_promo(tariff_id: int, data: dict):
        row = TariffRepository.get_by_id(tariff_id)
        if not row:
            raise AppError("Tarif tidak ditemukan.", 404)

        promo_type = _clean_text(data.get("promo_type")).lower()
        if promo_type not in ALLOWED_PROMO_TYPES:
            raise AppError("promo_type tidak valid.", 400)

        price = Decimal(str(row["price"]))
        promo_value = _parse_money(data.get("promo_value"), "diskon/promo")
        promo_start = _parse_date(data.get("promo_start"))
        promo_end = _parse_date(data.get("promo_end"))

        promo_type, promo_value, promo_start, promo_end = TariffService._validate_promo(
            price=price,
            promo_type=promo_type,
            promo_value=promo_value,
            promo_start=promo_start,
            promo_end=promo_end,
        )

        affected = TariffRepository.set_promo(
            tariff_id=tariff_id,
            promo_type=promo_type,
            promo_value=float(promo_value.quantize(Decimal("0.01"))),
            promo_start=promo_start,
            promo_end=promo_end,
        )
        if affected <= 0:
            raise AppError("Gagal menyimpan promo.", 400)