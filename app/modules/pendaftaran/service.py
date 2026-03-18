# app/modules/pendaftaran/service.py

from datetime import date, datetime
from typing import Any, Dict, Optional

from app.common.errors import AppError
from .repository import PendaftaranRepository


class PendaftaranService:

    # =========================
    # Helpers
    # =========================
    @staticmethod
    def _norm_str(v: Any) -> str:
        return str(v or "").strip()

    @staticmethod
    def _to_float(v: Any, default: float = 0.0) -> float:
        try:
            if v is None or v == "":
                return default
            return float(v)
        except Exception:
            return default

    @staticmethod
    def _to_int(v: Any, default: int = 0) -> int:
        try:
            if v is None or v == "":
                return default
            return int(v)
        except Exception:
            return default

    @staticmethod
    def _upper(v: Any) -> str:
        return PendaftaranService._norm_str(v).upper()

    @staticmethod
    def _parse_dt(dt_str: Any) -> str:
        """
        Input dari form biasanya: 'YYYY-MM-DDTHH:MM' (datetime-local) atau 'YYYY-MM-DD HH:MM:SS'
        Kita biarkan fleksibel, tapi tetap wajib ada.
        """
        s = PendaftaranService._norm_str(dt_str)
        if not s:
            raise AppError("Tanggal pendaftaran wajib diisi.", 400)
        return s

    @staticmethod
    def _ensure_header_exists(pendaftaran_id: int) -> Dict:
        header = PendaftaranRepository.get_header(pendaftaran_id)
        if not header:
            raise AppError("Pendaftaran tidak ditemukan.", 404)
        return header

    @staticmethod
    def _ensure_draft(header: Dict):
        if (header.get("status") or "").strip() not in ["draft", "confirmed"]:
            raise AppError("Pendaftaran sudah dikonfirmasi/dibatalkan. Tidak boleh diubah.", 400)

    @staticmethod
    def _ensure_status(header: Dict, allowed: set, msg: str):
        st = (header.get("status") or "").strip()
        if st not in allowed:
            raise AppError(msg, 400)

    @staticmethod
    def _is_promo_active(tariff_row: Dict, today: Optional[date] = None) -> bool:
        """
        promo_type/promo_value/promo_start/promo_end ada di master_tariff.
        """
        today = today or date.today()
        promo_type = (tariff_row.get("promo_type") or "").strip()
        if not promo_type:
            return False

        start = tariff_row.get("promo_start")
        end = tariff_row.get("promo_end")

        # mysql connector kadang mengembalikan datetime
        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()

        if start and today < start:
            return False
        if end and today > end:
            return False

        return True

    @staticmethod
    def _calc_discount_amount(gross: float, discount_type: Optional[str], discount_value: float) -> float:
        gross = max(0.0, gross)
        dt = PendaftaranService._upper(discount_type)
        dv = max(0.0, PendaftaranService._to_float(discount_value, 0.0))

        if dt == "PERCENT":
            disc = gross * (dv / 100.0)
        elif dt == "AMOUNT":
            disc = dv
        else:
            disc = 0.0

        if disc < 0:
            disc = 0.0
        if disc > gross:
            disc = gross
        return disc

    @staticmethod
    def _compute_row(qty: float, unit_price: float, discount_type: Optional[str], discount_value: float) -> Dict[str, float]:
        # qty harus integer >= 1 (sesuai UI qty step 1)
        try:
            qty_i = int(qty)
        except Exception:
            qty_i = 1
        if qty_i < 1:
            raise AppError("Qty minimal 1.", 400)

        unit_price = PendaftaranService._to_float(unit_price, 0.0)
        if unit_price < 0:
            unit_price = 0.0

        gross = qty_i * unit_price
        discount_amount = PendaftaranService._calc_discount_amount(gross, discount_type, discount_value)
        subtotal = gross - discount_amount
        if subtotal < 0:
            subtotal = 0.0

        return {
            "qty": float(qty_i),          # keep float kalau DB kolomnya numeric/decimal
            "qty_int": qty_i,             # helper kalau butuh int
            "unit_price": unit_price,
            "gross": gross,
            "discount_amount": discount_amount,
            "subtotal": subtotal,
        }

    # =========================
    # MASTER TARIFF
    # =========================
    @staticmethod
    def _must_get_master_tariff(tariff_id: int) -> Dict:
        tariff = PendaftaranRepository.get_master_tariff(tariff_id)
        if not tariff:
            raise AppError("Tarif tidak ditemukan / tidak aktif.", 404)
        return tariff

    @staticmethod
    def _resolve_pricing_from_master(tariff: Dict) -> Dict:
        """
        Backend yang memutuskan harga/diskon/promo.
        Frontend hanya kirim: tariff_id, qty, notes.
        """
        unit_price = tariff.get("final_price", None)
        if unit_price is None or unit_price == "":
            unit_price = tariff.get("price", 0)

        discount_type = tariff.get("discount_type")
        discount_value = tariff.get("discount_value", 0)

        # Jika master tidak punya discount_type, cek promo aktif -> gunakan promo sebagai diskon
        if (not PendaftaranService._norm_str(discount_type)) and PendaftaranService._is_promo_active(tariff):
            pt = PendaftaranService._upper(tariff.get("promo_type"))
            pv = PendaftaranService._to_float(tariff.get("promo_value"), 0.0)
            if pt in ("AMOUNT", "PERCENT"):
                discount_type = pt
                discount_value = pv

        promo_code = PendaftaranService._norm_str(tariff.get("promo_code")) or None
        promo_name = PendaftaranService._norm_str(tariff.get("promo_name")) or None

        return {
            "unit_price": unit_price,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "promo_code": promo_code,
            "promo_name": promo_name,
        }

    # =========================
    # HEADER
    # =========================
    @staticmethod
    def create_header(data: Dict) -> int:
        patient_code = PendaftaranService._norm_str(data.get("patient_code"))
        if not patient_code:
            raise AppError("Kode pasien wajib diisi.", 400)

        tgl = PendaftaranService._parse_dt(data.get("tgl_pendaftaran"))
        anam = PendaftaranService._norm_str(data.get("anamnesis_umum"))

        new_id = PendaftaranRepository.insert_header({
            "patient_code": patient_code,
            "tgl_pendaftaran": tgl,
            "anamnesis_umum": anam,
        })
        return new_id

    @staticmethod
    def edit_header(pendaftaran_id: int, data: Dict):
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)
        PendaftaranService._ensure_draft(header)

        patient_code = PendaftaranService._norm_str(data.get("patient_code"))
        if not patient_code:
            raise AppError("Kode pasien wajib diisi.", 400)

        tgl = PendaftaranService._parse_dt(data.get("tgl_pendaftaran"))
        anam = PendaftaranService._norm_str(data.get("anamnesis_umum"))

        PendaftaranRepository.update_header(pendaftaran_id, {
            "patient_code": patient_code,
            "tgl_pendaftaran": tgl,
            "anamnesis_umum": anam,
        })

    @staticmethod
    def confirm(pendaftaran_id: int):
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)
        if (header.get("status") or "").strip() != "draft":
            raise AppError("Status bukan draft.", 400)

        details = PendaftaranRepository.list_treatments(pendaftaran_id)
        if not details:
            raise AppError("Minimal 1 treatment sebelum konfirmasi.", 400)

        PendaftaranRepository.confirm(pendaftaran_id)

    @staticmethod
    def cancel(pendaftaran_id: int):
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)
        if (header.get("status") or "").strip() == "canceled":
            return
        PendaftaranRepository.cancel(pendaftaran_id)

    # =========================
    # PAID
    # =========================
    @staticmethod
    def set_paid(pendaftaran_id: int, paid_amount: Any):
        """
        Ubah status dari confirmed -> paid dan set paidAmount.
        paid_amount boleh string rupiah "150.000" atau angka.
        """
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)

        # Rekomendasi rule: hanya confirmed yang boleh jadi paid
        PendaftaranService._ensure_status(
            header,
            allowed={"confirmed"},
            msg="Hanya status confirmed yang boleh di-set menjadi paid.",
        )

        # Validasi nominal
        # delegate parsing ke repository._safe_float agar konsisten (terima "150.000")
        try:
            PendaftaranRepository.set_paid(pendaftaran_id, paid_amount)
        except ValueError as e:
            raise AppError(str(e), 400)

    # (opsional) kalau Anda butuh rollback
    @staticmethod
    def unset_paid(pendaftaran_id: int):
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)
        PendaftaranService._ensure_status(
            header,
            allowed={"paid"},
            msg="Hanya status paid yang bisa di-unset.",
        )
        PendaftaranRepository.unset_paid(pendaftaran_id)

    # =========================
    # TREATMENTS
    # =========================
    @staticmethod
    def add_treatment(pendaftaran_id: int, payload: Dict) -> int:
        """
        Frontend (modal DataTables) hanya mengirim minimal:
          - tariff_id (wajib)
          - qty (integer >=1)
          - notes (opsional) -> hanya dipakai kalau kolom notes ada di detail table

        Pricing/discount dikunci dari master:
          - unit_price ambil dari master_tariff.price
          - diskon default: tidak ada
          - jika promo aktif (promo_type/promo_value + range tanggal), maka diskon mengikuti promo tsb
        """
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)
        PendaftaranService._ensure_draft(header)

        tariff_id = PendaftaranService._to_int(payload.get("tariff_id"), 0)
        if tariff_id <= 0:
            raise AppError("Tariff wajib dipilih.", 400)

        tariff = PendaftaranService._must_get_master_tariff(tariff_id)

        # qty integer
        qty = PendaftaranService._to_int(payload.get("qty"), 1)
        if qty < 1:
            raise AppError("Qty minimal 1.", 400)

        # ===== LOCK PRICING dari master (yang ada di schema Anda) =====
        unit_price = tariff.get("price", 0)
        if unit_price is None or unit_price == "":
            unit_price = 0

        # diskon default none
        discount_type = None
        discount_value = 0

        # promo (kalau aktif) dipakai jadi diskon
        if PendaftaranService._is_promo_active(tariff):
            pt = PendaftaranService._upper(tariff.get("promo_type"))
            pv = PendaftaranService._to_float(tariff.get("promo_value"), 0.0)
            if pt in ("AMOUNT", "PERCENT"):
                discount_type = pt
                discount_value = pv

        calc = PendaftaranService._compute_row(qty, unit_price, discount_type, discount_value)

        # notes opsional (hanya kalau tabel pendaftaran_treatment ada kolom notes)
        notes = PendaftaranService._norm_str(payload.get("notes")) or None

        row = {
            "tariff_id": tariff["id"],
            "tariff_code": tariff.get("tariff_code"),
            "treatment_name_snapshot": tariff.get("treatment_name") or "",
            "qty": int(qty),
            "unit_price": calc["unit_price"],
            "discount_type": PendaftaranService._upper(discount_type) if PendaftaranService._norm_str(discount_type) else None,
            "discount_value": PendaftaranService._to_float(discount_value, 0.0),
            "discount_amount": calc["discount_amount"],
            "subtotal": calc["subtotal"],
        }

        # kalau repository insert_treatment sudah include notes, kita kirim
        row["notes"] = notes

        return PendaftaranRepository.insert_treatment(pendaftaran_id, row)

    @staticmethod
    def update_treatment(pendaftaran_id: int, detail_id: int, payload: Dict):
        """
        Tetap dipertahankan (kalau nanti Anda buat edit qty/diskon per item).
        Default: gunakan master tariff sebagai source of truth.
        """
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)
        PendaftaranService._ensure_draft(header)

        tariff_id = PendaftaranService._to_int(payload.get("tariff_id"), 0)
        if tariff_id <= 0:
            raise AppError("Tariff wajib dipilih.", 400)

        tariff = PendaftaranService._must_get_master_tariff(tariff_id)

        qty = PendaftaranService._to_int(payload.get("qty"), 1)
        if qty < 1:
            raise AppError("Qty minimal 1.", 400)

        notes = PendaftaranService._norm_str(payload.get("notes")) or None

        # lock dari master (sesuai UI)
        pricing = PendaftaranService._resolve_pricing_from_master(tariff)

        calc = PendaftaranService._compute_row(
            qty=qty,
            unit_price=pricing["unit_price"],
            discount_type=pricing["discount_type"],
            discount_value=pricing["discount_value"],
        )

        row = {
            "tariff_id": tariff["id"],
            "tariff_code": tariff.get("tariff_code"),
            "treatment_name_snapshot": tariff.get("treatment_name") or "",
            "qty": calc["qty_int"],
            "unit_price": calc["unit_price"],
            "discount_type": PendaftaranService._upper(pricing["discount_type"]) if PendaftaranService._norm_str(pricing["discount_type"]) else None,
            "discount_value": PendaftaranService._to_float(pricing["discount_value"], 0.0),
            "discount_amount": calc["discount_amount"],
            "promo_code": pricing["promo_code"],
            "promo_name": pricing["promo_name"],
            "notes": notes,
            "subtotal": calc["subtotal"],
        }

        PendaftaranRepository.update_treatment(pendaftaran_id, detail_id, row)

    @staticmethod
    def delete_treatment(pendaftaran_id: int, detail_id: int):
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)
        PendaftaranService._ensure_draft(header)

        PendaftaranRepository.delete_treatment(pendaftaran_id, detail_id)

    @staticmethod
    def paid(pendaftaran_id: int, paid_amount: Any) -> str:
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)

        if (header.get("status") or "").strip() != "confirmed":
            raise AppError("Status harus confirmed sebelum paid.", 400)

        details = PendaftaranRepository.list_treatments(pendaftaran_id)
        if not details:
            raise AppError("Minimal 1 treatment sebelum paid.", 400)

        try:
            PendaftaranRepository.set_paid(pendaftaran_id, paid_amount)
        except ValueError as e:
            raise AppError(str(e), 400)

        token = PendaftaranRepository.get_or_create_receipt_token(pendaftaran_id)
        return token
    
    @staticmethod
    def delete_header(pendaftaran_id: int):
        header = PendaftaranService._ensure_header_exists(pendaftaran_id)

        status = (header.get("status") or "").strip().lower()

        if status == "paid":
            raise AppError(
                "Pendaftaran berstatus paid tidak boleh dihapus. Lakukan unset paid terlebih dahulu.",
                400
            )

        if status not in {"draft", "canceled"}:
            raise AppError("Status pendaftaran tidak valid untuk dihapus.", 400)

        PendaftaranRepository.delete_header(pendaftaran_id)