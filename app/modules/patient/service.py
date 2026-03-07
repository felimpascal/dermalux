from typing import Optional
from app.common.errors import AppError
from .repository import PatientRepository


class PatientService:

    @staticmethod
    def _norm_str(v) -> str:
        return (v or "").strip()

    @staticmethod
    def _norm_opt(v) -> Optional[str]:
        s = (v or "").strip()
        return s if s else None

    @staticmethod
    def _digits_len(s: str) -> int:
        return len("".join([c for c in (s or "") if c.isdigit()]))

    @staticmethod
    def _validate_payload(payload: dict, for_update: bool = False) -> dict:
        """
        Normalisasi + validasi payload create/update.
        Return dict yang sudah bersih untuk repo.
        """

        full_name = PatientService._norm_str(payload.get("full_name"))
        birth_place = PatientService._norm_str(payload.get("birth_place"))
        birth_date = PatientService._norm_str(payload.get("birth_date"))  # expect YYYY-MM-DD
        gender = PatientService._norm_str(payload.get("gender"))
        address = PatientService._norm_str(payload.get("address"))
        phone = PatientService._norm_str(payload.get("phone"))

        nik = PatientService._norm_opt(payload.get("nik"))
        # patient_code jangan dipakai untuk update biasa (biarkan DB/generator), tapi
        # kalau Anda mau support input manual, boleh dipakai saat create.
        patient_code = PatientService._norm_opt(payload.get("patient_code"))

        # ====== wajib ======
        if not full_name:
            raise AppError("Nama wajib diisi.", 400)
        if not birth_place:
            raise AppError("Tempat lahir wajib diisi.", 400)
        if not birth_date:
            raise AppError("Tanggal lahir wajib diisi.", 400)
        if not gender:
            raise AppError("Jenis kelamin wajib diisi.", 400)
        if not address:
            raise AppError("Alamat wajib diisi.", 400)
        if not phone:
            raise AppError("No HP wajib diisi.", 400)

        # ====== validasi format ======
        if PatientService._digits_len(phone) < 8:
            raise AppError("No HP tidak valid (minimal 8 digit).", 400)

        if gender not in ("M", "F"):
            raise AppError("Jenis kelamin tidak valid. Gunakan 'M' atau 'F'.", 400)

        # NIK opsional, jika ada harus 16 digit angka
        if nik:
            if not nik.isdigit():
                raise AppError("NIK harus berupa angka.", 400)
            if len(nik) != 16:
                raise AppError("NIK wajib 16 digit (tidak lebih dan tidak kurang).", 400)

        return {
            "patient_code": patient_code,
            "nik": nik,
            "full_name": full_name,
            "birth_place": birth_place,
            "birth_date": birth_date,
            "gender": gender,
            "address": address,
            "phone": phone,
        }

    @staticmethod
    def create(payload: dict):
        p = PatientService._validate_payload(payload, for_update=False)

        # Jika Anda TIDAK ingin pasien input patient_code manual, force None di sini.
        p["patient_code"] = None

        return PatientRepository.insert(
            nik=p["nik"],
            full_name=p["full_name"],
            birth_place=p["birth_place"],
            birth_date=p["birth_date"],
            gender=p["gender"],
            address=p["address"],
            phone=p["phone"],
        )

    @staticmethod
    def search(q: str = "", limit: int = 50):
        # q boleh kosong -> latest
        q = (q or "").strip()
        try:
            limit_int = int(limit or 50)
        except Exception:
            limit_int = 50

        return PatientRepository.search(q=q, limit=limit_int)

    @staticmethod
    def get(patient_id: int):
        try:
            pid = int(patient_id)
        except Exception:
            raise AppError("patient_id tidak valid.", 400)

        if pid <= 0:
            raise AppError("patient_id tidak valid.", 400)

        row = PatientRepository.get_by_id(pid)
        if not row:
            raise AppError("Pasien tidak ditemukan.", 404)
        return row

    @staticmethod
    def get_by_code(patient_code: str):
        code = (patient_code or "").strip()
        if not code:
            raise AppError("patient_code tidak valid.", 400)

        row = PatientRepository.get_by_code(code)
        if not row:
            raise AppError("Pasien tidak ditemukan.", 404)
        return row

    @staticmethod
    def update(patient_id: int, payload: dict):
        try:
            pid = int(patient_id)
        except Exception:
            raise AppError("patient_id tidak valid.", 400)

        if pid <= 0:
            raise AppError("patient_id tidak valid.", 400)

        # cek eksistensi
        existing = PatientRepository.get_by_id(pid)
        if not existing:
            raise AppError("Pasien tidak ditemukan.", 404)

        p = PatientService._validate_payload(payload, for_update=True)

        # Saat update, jangan ubah patient_code (biarkan konsisten)
        return PatientRepository.update(
            patient_id=pid,
            nik=p["nik"],
            full_name=p["full_name"],
            birth_place=p["birth_place"],
            birth_date=p["birth_date"],
            gender=p["gender"],
            address=p["address"],
            phone=p["phone"],
        )