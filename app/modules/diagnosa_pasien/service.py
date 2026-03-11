from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import current_app, g, session
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from app.common.errors import AppError
from app.modules.authz.repository import PermissionRepository
from app.modules.diagnosa_pasien.repository import DiagnosaRepository
from app.modules.pendaftaran.repository import PendaftaranRepository


class DiagnosaService:
    """
    Service layer untuk modul diagnosa_pasien.

    Tugas utama:
    - validasi input
    - validasi permission
    - validasi ownership
    - orkestrasi repository
    - business rules:
        * 1 pendaftaran bisa banyak diagnosa
        * minimal 1 detail diagnosa
        * tepat 1 diagnosa utama
        * foto opsional
        * edit hanya oleh user berizin
        * delete oleh dokter sendiri / pembuat sendiri atau user berizin
    """

    # =========================
    # Permission Codes
    # =========================
    PERM_VIEW = "diagnosa_pasien.view"
    PERM_CREATE = "diagnosa_pasien.create"
    PERM_EDIT = "diagnosa_pasien.edit"
    PERM_EDIT_ALL = "diagnosa_pasien.edit_all"
    PERM_EDIT_OWN = "diagnosa_pasien.edit_own"
    PERM_DELETE = "diagnosa_pasien.delete"
    PERM_DELETE_ALL = "diagnosa_pasien.delete_all"
    PERM_DELETE_OWN = "diagnosa_pasien.delete_own"
    PERM_UPLOAD_FOTO = "diagnosa_pasien.foto_upload"
    PERM_DELETE_FOTO = "diagnosa_pasien.foto_delete"

    ALLOWED_JENIS_FOTO = {"before", "after", "progress", "other"}
    ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    # =========================
    # Public - Master
    # =========================
    @staticmethod
    def list_master_diagnosa(search: str = "", limit: int = 5000) -> List[Dict]:
        DiagnosaService._ensure_logged_in()
        return DiagnosaRepository.list_master_diagnosa(
            search=(search or "").strip(),
            is_active=1,
            limit=limit,
        )

    @staticmethod
    def get_master_diagnosa(master_diagnosa_id: int) -> Dict:
        DiagnosaService._ensure_logged_in()

        row = DiagnosaRepository.get_master_diagnosa(DiagnosaService._to_int(master_diagnosa_id))
        if not row:
            raise AppError("Master diagnosa tidak ditemukan.", 404)

        return row

    # =========================
    # Public - List / View
    # =========================
    @staticmethod
    def list_by_pendaftaran(pendaftaran_id: int) -> List[Dict]:
        DiagnosaService._ensure_logged_in()
        DiagnosaService._assert_has_any_permission(
            [DiagnosaService.PERM_VIEW, DiagnosaService.PERM_CREATE, DiagnosaService.PERM_EDIT]
        )

        pendaftaran_id = DiagnosaService._to_int(pendaftaran_id)
        if pendaftaran_id <= 0:
            raise AppError("pendaftaran_id tidak valid.", 400)

        header = PendaftaranRepository.get_header(pendaftaran_id)
        if not header:
            raise AppError("Data pendaftaran tidak ditemukan.", 404)

        return DiagnosaRepository.list_headers_by_pendaftaran(pendaftaran_id)

    @staticmethod
    def get_full(diagnosa_id: int) -> Dict:
        DiagnosaService._ensure_logged_in()
        DiagnosaService._assert_has_any_permission(
            [DiagnosaService.PERM_VIEW, DiagnosaService.PERM_EDIT, DiagnosaService.PERM_DELETE]
        )

        diagnosa_id = DiagnosaService._to_int(diagnosa_id)
        if diagnosa_id <= 0:
            raise AppError("diagnosa_id tidak valid.", 400)

        data = DiagnosaRepository.get_full(diagnosa_id)
        if not data:
            raise AppError("Data diagnosa tidak ditemukan.", 404)

        return data

    # =========================
    # Public - Create / Update / Delete
    # =========================
    @staticmethod
    def create(payload: Dict) -> Dict:
        DiagnosaService._ensure_logged_in()
        DiagnosaService._assert_has_permission(DiagnosaService.PERM_CREATE)

        user_id = DiagnosaService._get_current_user_id()

        data = DiagnosaService._normalize_header_payload(payload, for_update=False)
        details = DiagnosaService._normalize_details_payload(payload.get("diagnosa_details"))
        photos = DiagnosaService._normalize_uploaded_photos_payload(
            payload.get("photos"),
            payload.get("uploaded_files"),
        )

        DiagnosaService._validate_pendaftaran_exists(data["pendaftaran_id"])
        DiagnosaService._validate_details(details)
        DiagnosaService._validate_uploaded_photos(photos)

        data["created_by"] = user_id
        data["updated_by"] = user_id

        # create header + detail dulu, foto menyusul
        diagnosa_id = DiagnosaRepository.create_full(data=data, details=details, photos=None)

        for photo in photos:
            saved = DiagnosaService._save_uploaded_photo(photo["file_storage"])

            DiagnosaRepository.insert_photo(
                diagnosa_id=diagnosa_id,
                row={
                    "jenis_foto": photo.get("jenis_foto"),
                    "area_foto": photo.get("area_foto"),
                    "file_name": saved["file_name"],
                    "file_path": saved["file_path"],
                    "taken_at": photo.get("taken_at"),
                    "uploaded_by": user_id,
                    "note": photo.get("note"),
                },
            )

        return DiagnosaService.get_full(diagnosa_id)

    @staticmethod
    def update(diagnosa_id: int, payload: Dict) -> Dict:
        DiagnosaService._ensure_logged_in()

        diagnosa_id = DiagnosaService._to_int(diagnosa_id)
        if diagnosa_id <= 0:
            raise AppError("diagnosa_id tidak valid.", 400)

        owner = DiagnosaRepository.get_owner_info(diagnosa_id)
        if not owner or int(owner.get("is_deleted") or 0) == 1:
            raise AppError("Data diagnosa tidak ditemukan.", 404)

        DiagnosaService._assert_can_edit(owner)

        data = DiagnosaService._normalize_header_payload(payload, for_update=True)
        details = DiagnosaService._normalize_details_payload(payload.get("diagnosa_details"))
        photos = DiagnosaService._normalize_uploaded_photos_payload(
            payload.get("photos"),
            payload.get("uploaded_files"),
        )

        DiagnosaService._validate_details(details)
        DiagnosaService._validate_uploaded_photos(photos)

        data["updated_by"] = DiagnosaService._get_current_user_id()

        DiagnosaRepository.update_full(
            diagnosa_id=diagnosa_id,
            data=data,
            details=details,
        )

        for photo in photos:
            saved = DiagnosaService._save_uploaded_photo(photo["file_storage"])

            DiagnosaRepository.insert_photo(
                diagnosa_id=diagnosa_id,
                row={
                    "jenis_foto": photo.get("jenis_foto"),
                    "area_foto": photo.get("area_foto"),
                    "file_name": saved["file_name"],
                    "file_path": saved["file_path"],
                    "taken_at": photo.get("taken_at"),
                    "uploaded_by": DiagnosaService._get_current_user_id(),
                    "note": photo.get("note"),
                },
            )

        return DiagnosaService.get_full(diagnosa_id)

    @staticmethod
    def delete(diagnosa_id: int) -> Dict:
        DiagnosaService._ensure_logged_in()

        diagnosa_id = DiagnosaService._to_int(diagnosa_id)
        if diagnosa_id <= 0:
            raise AppError("diagnosa_id tidak valid.", 400)

        owner = DiagnosaRepository.get_owner_info(diagnosa_id)
        if not owner:
            raise AppError("Data diagnosa tidak ditemukan.", 404)

        if int(owner.get("is_deleted") or 0) == 1:
            raise AppError("Data diagnosa sudah dihapus.", 400)

        DiagnosaService._assert_can_delete(owner)

        user_id = DiagnosaService._get_current_user_id()
        DiagnosaRepository.soft_delete(diagnosa_id, deleted_by=user_id)

        return {
            "ok": True,
            "message": "Diagnosa berhasil dihapus.",
            "diagnosa_id": diagnosa_id,
        }

    # =========================
    # Public - Photos
    # =========================
    @staticmethod
    def add_photo(diagnosa_id: int, payload: Dict) -> Dict:
        DiagnosaService._ensure_logged_in()

        diagnosa_id = DiagnosaService._to_int(diagnosa_id)
        if diagnosa_id <= 0:
            raise AppError("diagnosa_id tidak valid.", 400)

        owner = DiagnosaRepository.get_owner_info(diagnosa_id)
        if not owner or int(owner.get("is_deleted") or 0) == 1:
            raise AppError("Data diagnosa tidak ditemukan.", 404)

        if not DiagnosaService._has_any_permission(
            [DiagnosaService.PERM_UPLOAD_FOTO, DiagnosaService.PERM_EDIT, DiagnosaService.PERM_EDIT_ALL]
        ):
            DiagnosaService._assert_can_edit(owner)

        # Endpoint ini tetap mendukung mode lama:
        # payload berisi file_name/file_path, bukan request.files
        rows = DiagnosaService._normalize_photos_payload([payload])
        DiagnosaService._validate_photos(rows)

        row = rows[0]
        row["uploaded_by"] = DiagnosaService._get_current_user_id()

        foto_id = DiagnosaRepository.insert_photo(diagnosa_id, row)
        photo = DiagnosaRepository.get_photo(foto_id)

        return {
            "ok": True,
            "message": "Foto berhasil ditambahkan.",
            "photo": photo,
        }

    @staticmethod
    def delete_photo(foto_id: int) -> Dict:
        DiagnosaService._ensure_logged_in()

        foto_id = DiagnosaService._to_int(foto_id)
        if foto_id <= 0:
            raise AppError("foto_id tidak valid.", 400)

        photo = DiagnosaRepository.get_photo(foto_id)
        if not photo:
            raise AppError("Foto tidak ditemukan.", 404)

        owner = DiagnosaRepository.get_owner_info(DiagnosaService._to_int(photo.get("diagnosa_id")))
        if not owner or int(owner.get("is_deleted") or 0) == 1:
            raise AppError("Diagnosa induk tidak ditemukan.", 404)

        if not DiagnosaService._has_any_permission(
            [DiagnosaService.PERM_DELETE_FOTO, DiagnosaService.PERM_EDIT, DiagnosaService.PERM_EDIT_ALL]
        ):
            DiagnosaService._assert_can_edit(owner)

        DiagnosaRepository.delete_photo(foto_id)

        return {
            "ok": True,
            "message": "Foto berhasil dihapus.",
            "foto_id": foto_id,
        }

    # =========================
    # Public - Helpers for UI
    # =========================
    @staticmethod
    def get_form_context_create(pendaftaran_id: int) -> Dict:
        DiagnosaService._ensure_logged_in()
        DiagnosaService._assert_has_permission(DiagnosaService.PERM_CREATE)

        pendaftaran_id = DiagnosaService._to_int(pendaftaran_id)
        if pendaftaran_id <= 0:
            raise AppError("pendaftaran_id tidak valid.", 400)

        pendaftaran = PendaftaranRepository.get_header(pendaftaran_id)
        if not pendaftaran:
            raise AppError("Data pendaftaran tidak ditemukan.", 404)

        master_diagnosa = DiagnosaRepository.list_master_diagnosa(is_active=1, limit=5000)

        return {
            "pendaftaran": pendaftaran,
            "master_diagnosa": master_diagnosa,
        }

    @staticmethod
    def get_form_context_edit(diagnosa_id: int) -> Dict:
        DiagnosaService._ensure_logged_in()

        diagnosa_id = DiagnosaService._to_int(diagnosa_id)
        if diagnosa_id <= 0:
            raise AppError("diagnosa_id tidak valid.", 400)

        owner = DiagnosaRepository.get_owner_info(diagnosa_id)
        if not owner or int(owner.get("is_deleted") or 0) == 1:
            raise AppError("Data diagnosa tidak ditemukan.", 404)

        DiagnosaService._assert_can_edit(owner)

        full = DiagnosaRepository.get_full(diagnosa_id)
        if not full:
            raise AppError("Data diagnosa tidak ditemukan.", 404)

        master_diagnosa = DiagnosaRepository.list_master_diagnosa(is_active=1, limit=5000)

        return {
            "data": full,
            "master_diagnosa": master_diagnosa,
        }

    # =========================
    # Internal - Validation
    # =========================
    @staticmethod
    def _validate_pendaftaran_exists(pendaftaran_id: int):
        row = PendaftaranRepository.get_header(pendaftaran_id)
        if not row:
            raise AppError("Data pendaftaran tidak ditemukan.", 404)

    @staticmethod
    def _validate_details(details: List[Dict]):
        if not details:
            raise AppError("Minimal harus ada 1 diagnosa.", 400)

        primary_count = 0
        seen_ids = set()

        for i, row in enumerate(details, start=1):
            master_diagnosa_id = DiagnosaService._to_int(row.get("master_diagnosa_id"))
            if master_diagnosa_id <= 0:
                raise AppError(f"Diagnosa ke-{i} tidak valid.", 400)

            if master_diagnosa_id in seen_ids:
                raise AppError("Diagnosa yang sama tidak boleh dipilih lebih dari satu kali.", 400)
            seen_ids.add(master_diagnosa_id)

            master = DiagnosaRepository.get_master_diagnosa(master_diagnosa_id)
            if not master:
                raise AppError(f"Master diagnosa ke-{i} tidak ditemukan.", 400)

            if int(master.get("is_active") or 0) != 1:
                raise AppError(f"Master diagnosa '{master.get('diagnosa_name')}' tidak aktif.", 400)

            if int(row.get("is_primary") or 0) == 1:
                primary_count += 1

        if primary_count == 0:
            raise AppError("Harus ada 1 diagnosa utama.", 400)

        if primary_count > 1:
            raise AppError("Diagnosa utama hanya boleh 1.", 400)

    @staticmethod
    def _validate_photos(photos: List[Dict]):
        for i, row in enumerate(photos or [], start=1):
            file_name = (row.get("file_name") or "").strip()
            if not file_name:
                raise AppError(f"Foto ke-{i}: file_name wajib diisi.", 400)

            jenis_foto = (row.get("jenis_foto") or "").strip().lower()
            if not jenis_foto:
                raise AppError(f"Foto ke-{i}: jenis_foto wajib diisi.", 400)

            if jenis_foto not in DiagnosaService.ALLOWED_JENIS_FOTO:
                raise AppError(
                    f"Foto ke-{i}: jenis_foto tidak valid. "
                    f"Gunakan salah satu dari {sorted(DiagnosaService.ALLOWED_JENIS_FOTO)}.",
                    400,
                )

    @staticmethod
    def _validate_uploaded_photos(photos: List[Dict]):
        for i, row in enumerate(photos or [], start=1):
            jenis_foto = (row.get("jenis_foto") or "").strip().lower()
            if not jenis_foto:
                raise AppError(f"Foto ke-{i}: jenis_foto wajib diisi.", 400)

            if jenis_foto not in DiagnosaService.ALLOWED_JENIS_FOTO:
                raise AppError(
                    f"Foto ke-{i}: jenis_foto tidak valid. "
                    f"Gunakan salah satu dari {sorted(DiagnosaService.ALLOWED_JENIS_FOTO)}.",
                    400,
                )

            file_storage = row.get("file_storage")
            if not file_storage or not getattr(file_storage, "filename", ""):
                raise AppError(f"Foto ke-{i}: file wajib dipilih.", 400)

            ext = os.path.splitext(secure_filename(file_storage.filename or ""))[1].lower()
            if ext not in DiagnosaService.ALLOWED_PHOTO_EXTENSIONS:
                raise AppError(
                    f"Foto ke-{i}: format file tidak didukung. "
                    f"Gunakan salah satu dari {sorted(DiagnosaService.ALLOWED_PHOTO_EXTENSIONS)}.",
                    400,
                )

    # =========================
    # Internal - Normalize Payload
    # =========================
    @staticmethod
    def _normalize_header_payload(payload: Dict, for_update: bool = False) -> Dict:
        if not isinstance(payload, dict):
            raise AppError("Payload tidak valid.", 400)

        data: Dict[str, Any] = {}

        if not for_update:
            data["pendaftaran_id"] = DiagnosaService._to_int(payload.get("pendaftaran_id"))
            if data["pendaftaran_id"] <= 0:
                raise AppError("pendaftaran_id wajib diisi.", 400)

        dokter_id = payload.get("dokter_id")
        data["dokter_id"] = (
            DiagnosaService._to_int(dokter_id)
            if dokter_id not in (None, "", 0, "0")
            else None
        )

        raw_tgl = (payload.get("tgl_diagnosa") or "").strip()
        data["tgl_diagnosa"] = (
            DiagnosaService._normalize_datetime(raw_tgl)
            if raw_tgl
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        data["keluhan_utama"] = DiagnosaService._nullable_str(payload.get("keluhan_utama"))
        data["anamnesis_dokter"] = DiagnosaService._nullable_str(payload.get("anamnesis_dokter"))
        data["pemeriksaan_fisik"] = DiagnosaService._nullable_str(payload.get("pemeriksaan_fisik"))
        data["jenis_kulit"] = DiagnosaService._nullable_str(payload.get("jenis_kulit"))
        data["lokasi_keluhan"] = DiagnosaService._nullable_str(payload.get("lokasi_keluhan"))
        data["durasi_keluhan"] = DiagnosaService._nullable_str(payload.get("durasi_keluhan"))
        data["riwayat_alergi"] = DiagnosaService._nullable_str(payload.get("riwayat_alergi"))
        data["riwayat_perawatan"] = DiagnosaService._nullable_str(payload.get("riwayat_perawatan"))
        data["assessment"] = DiagnosaService._nullable_str(payload.get("assessment"))
        data["rencana_tindakan"] = DiagnosaService._nullable_str(payload.get("rencana_tindakan"))
        data["edukasi_pasien"] = DiagnosaService._nullable_str(payload.get("edukasi_pasien"))
        data["saran_kontrol"] = DiagnosaService._nullable_str(payload.get("saran_kontrol"))

        return data

    @staticmethod
    def _normalize_details_payload(rows: Any) -> List[Dict]:
        if rows is None:
            rows = []

        if not isinstance(rows, list):
            raise AppError("diagnosa_details harus berupa array/list.", 400)

        out: List[Dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            master_diagnosa_id = DiagnosaService._to_int(row.get("master_diagnosa_id"))
            is_primary = 1 if DiagnosaService._to_int(row.get("is_primary")) == 1 else 0
            note = DiagnosaService._nullable_str(row.get("note"))

            if master_diagnosa_id <= 0:
                continue

            out.append(
                {
                    "master_diagnosa_id": master_diagnosa_id,
                    "is_primary": is_primary,
                    "note": note,
                }
            )

        return out

    @staticmethod
    def _normalize_photos_payload(rows: Any) -> List[Dict]:
        """
        Mode lama / manual:
        photos berisi file_name dan file_path langsung.
        Dipakai oleh add_photo() lama.
        """
        if rows is None:
            rows = []

        if not isinstance(rows, list):
            raise AppError("photos harus berupa array/list.", 400)

        out: List[Dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            file_name = DiagnosaService._nullable_str(row.get("file_name"))
            file_path = DiagnosaService._nullable_str(row.get("file_path"))
            jenis_foto = (row.get("jenis_foto") or "").strip().lower()
            area_foto = DiagnosaService._nullable_str(row.get("area_foto"))
            note = DiagnosaService._nullable_str(row.get("note"))
            uploaded_by = DiagnosaService._to_int(row.get("uploaded_by")) or None

            raw_taken_at = (row.get("taken_at") or "").strip() if row.get("taken_at") is not None else ""
            taken_at = DiagnosaService._normalize_datetime(raw_taken_at) if raw_taken_at else None

            if not file_name and not file_path and not jenis_foto:
                continue

            out.append(
                {
                    "jenis_foto": jenis_foto,
                    "area_foto": area_foto,
                    "file_name": file_name,
                    "file_path": file_path,
                    "taken_at": taken_at,
                    "uploaded_by": uploaded_by,
                    "note": note,
                }
            )

        return out

    @staticmethod
    def _normalize_uploaded_photos_payload(
        rows: Any,
        uploaded_files: Optional[ImmutableMultiDict] = None,
    ) -> List[Dict]:
        """
        Mode upload form:
        - rows berasal dari photos_meta
        - file asli berasal dari request.files
        """
        if rows is None:
            rows = []

        if not isinstance(rows, list):
            raise AppError("photos harus berupa array/list.", 400)

        out: List[Dict] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            input_name = DiagnosaService._safe_form_str(row.get("input_name"))
            jenis_foto = DiagnosaService._safe_form_str(row.get("jenis_foto")).lower()
            area_foto = DiagnosaService._nullable_str(row.get("area_foto"))
            note = DiagnosaService._nullable_str(row.get("note"))

            raw_taken_at = DiagnosaService._safe_form_str(row.get("taken_at"))
            taken_at = DiagnosaService._normalize_datetime(raw_taken_at) if raw_taken_at else None

            file_storage = uploaded_files.get(input_name) if uploaded_files and input_name else None
            has_file = bool(file_storage and getattr(file_storage, "filename", ""))

            if not jenis_foto and not area_foto and not raw_taken_at and not note and not has_file:
                continue

            out.append(
                {
                    "input_name": input_name,
                    "jenis_foto": jenis_foto,
                    "area_foto": area_foto,
                    "taken_at": taken_at,
                    "note": note,
                    "file_storage": file_storage,
                    "has_file": has_file,
                }
            )

        return out

    # =========================
    # Internal - File Upload
    # =========================
    @staticmethod
    def _save_uploaded_photo(file_storage):
        if not file_storage or not file_storage.filename:
            raise AppError("File foto tidak valid.", 400)

        original_name = secure_filename(file_storage.filename or "")
        ext = os.path.splitext(original_name)[1].lower()

        if ext not in DiagnosaService.ALLOWED_PHOTO_EXTENSIONS:
            raise AppError("Format file foto tidak didukung.", 400)

        new_name = f"{uuid.uuid4().hex}{ext}"

        upload_dir = os.path.join(current_app.static_folder, "uploads", "diagnosa_pasien")
        os.makedirs(upload_dir, exist_ok=True)

        abs_path = os.path.join(upload_dir, new_name)
        file_storage.save(abs_path)

        return {
            "file_name": original_name,
            "file_path": f"diagnosa_pasien/{new_name}",
        }

    # =========================
    # Internal - Permission / Ownership
    # =========================
    @staticmethod
    def _assert_can_edit(owner: Dict):
        if DiagnosaService._is_admin():
            return

        if DiagnosaService._has_any_permission(
            [DiagnosaService.PERM_EDIT_ALL, DiagnosaService.PERM_EDIT]
        ):
            return

        current_user_id = DiagnosaService._get_current_user_id()
        created_by = DiagnosaService._to_int(owner.get("created_by"))

        if created_by > 0 and current_user_id == created_by:
            if DiagnosaService._has_permission(DiagnosaService.PERM_EDIT_OWN):
                return

        raise AppError("Anda tidak memiliki hak akses untuk mengubah diagnosa ini.", 403)

    @staticmethod
    def _assert_can_delete(owner: Dict):
        if DiagnosaService._is_admin():
            return

        if DiagnosaService._has_any_permission(
            [DiagnosaService.PERM_DELETE_ALL, DiagnosaService.PERM_DELETE]
        ):
            return

        current_user_id = DiagnosaService._get_current_user_id()
        created_by = DiagnosaService._to_int(owner.get("created_by"))
        dokter_id = DiagnosaService._to_int(owner.get("dokter_id"))

        if current_user_id in {created_by, dokter_id}:
            if DiagnosaService._has_permission(DiagnosaService.PERM_DELETE_OWN):
                return

        raise AppError("Anda tidak memiliki hak akses untuk menghapus diagnosa ini.", 403)

    @staticmethod
    def _assert_has_permission(permission_code: str):
        if DiagnosaService._is_admin():
            return

        if not DiagnosaService._has_permission(permission_code):
            raise AppError("FORBIDDEN", 403)

    @staticmethod
    def _assert_has_any_permission(permission_codes: List[str]):
        if DiagnosaService._is_admin():
            return

        if not DiagnosaService._has_any_permission(permission_codes):
            raise AppError("FORBIDDEN", 403)

    @staticmethod
    def _has_any_permission(permission_codes: List[str]) -> bool:
        for code in permission_codes or []:
            if DiagnosaService._has_permission(code):
                return True
        return False

    @staticmethod
    def _has_permission(permission_code: str) -> bool:
        user_id = DiagnosaService._get_current_user_id(raise_if_missing=False)
        if not user_id:
            return False

        try:
            return PermissionRepository.has_permission_user_id(int(user_id), permission_code)
        except Exception:
            return False

    # =========================
    # Internal - Session / User
    # =========================
    @staticmethod
    def _ensure_logged_in():
        DiagnosaService._get_current_user_id(raise_if_missing=True)

    @staticmethod
    def _get_current_user_id(raise_if_missing: bool = True) -> Optional[int]:
        user_id = None

        if hasattr(g, "user") and isinstance(g.user, dict):
            user_id = g.user.get("id")

        if not user_id:
            user_id = session.get("user_id")

        user_id = DiagnosaService._to_int(user_id)

        if raise_if_missing and user_id <= 0:
            raise AppError("Unauthorized", 401)

        return user_id if user_id > 0 else None

    @staticmethod
    def _is_admin() -> bool:
        try:
            return session.get("role") == "admin"
        except Exception:
            return False

    # =========================
    # Internal - Generic Utils
    # =========================
    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _nullable_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _safe_form_str(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _normalize_datetime(value: str) -> str:
        """
        Terima beberapa format umum, kembalikan string 'YYYY-mm-dd HH:MM:SS'
        yang aman untuk MySQL connector.
        """
        if not value:
            raise AppError("Tanggal/waktu tidak valid.", 400)

        candidates = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        ]

        for fmt in candidates:
            try:
                dt = datetime.strptime(value, fmt)
                if fmt == "%Y-%m-%d":
                    dt = dt.replace(hour=0, minute=0, second=0)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        raise AppError("Format tanggal/waktu tidak valid.", 400)



    def get_daily_sales_summary_service(tanggal: str):
        tanggal = (tanggal or "").strip()

        if not tanggal:
            raise AppError("Tanggal wajib diisi.", 400)

        try:
            datetime.strptime(tanggal, "%Y-%m-%d")
        except ValueError:
            raise AppError("Tanggal harus berformat YYYY-MM-DD.", 400)

        row = DiagnosaRepository.get_daily_sales_summary_repo(tanggal)

        return {
            "tanggal": tanggal,
            "total_transaksi": row.get("total_transaksi", 0),
            "total_penerimaan_uang": row.get("total_penerimaan_uang", 0)
        }