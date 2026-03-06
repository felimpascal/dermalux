from app.common.errors import AppError
from .repository import DiagnosaRepository

class DiagnosaService:

    @staticmethod
    def normalize_and_validate(data: dict, diagnosa_id: int | None = None) -> dict:
        code = (data.get("diagnosa_code") or "").strip()
        name = (data.get("diagnosa_name") or "").strip()

        if not code:
            raise AppError("Kode diagnosa wajib diisi.", 400)
        if not name:
            raise AppError("Nama diagnosa wajib diisi.", 400)

        try:
            is_active = int(data.get("is_active", 1))
        except Exception:
            is_active = 1
        is_active = 1 if is_active == 1 else 0

        # unique code
        existing = DiagnosaRepository.get_by_code(code)
        if existing and (diagnosa_id is None or int(existing["id"]) != int(diagnosa_id)):
            raise AppError("Kode diagnosa sudah digunakan.", 400)

        return {"diagnosa_code": code, "diagnosa_name": name, "is_active": is_active}

    @staticmethod
    def create(data: dict) -> int:
        payload = DiagnosaService.normalize_and_validate(data, None)
        return DiagnosaRepository.insert(payload)

    @staticmethod
    def edit(diagnosa_id: int, data: dict):
        payload = DiagnosaService.normalize_and_validate(data, diagnosa_id)
        affected = DiagnosaRepository.update(diagnosa_id, payload)
        if affected <= 0:
            raise AppError("Data diagnosa tidak ditemukan / tidak berubah.", 404)

    @staticmethod
    def disable(diagnosa_id: int):
        affected = DiagnosaRepository.set_active(diagnosa_id, 0)
        if affected <= 0:
            raise AppError("Data diagnosa tidak ditemukan.", 404)

    @staticmethod
    def enable(diagnosa_id: int):
        affected = DiagnosaRepository.set_active(diagnosa_id, 1)
        if affected <= 0:
            raise AppError("Data diagnosa tidak ditemukan.", 404)