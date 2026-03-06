# app/modules/riwayat_pasien/service.py

from typing import Any, Dict, List
from app.common.errors import AppError
from .repository import RiwayatPasienRepository


class RiwayatPasienService:

    # =========================
    # Helpers
    # =========================
    @staticmethod
    def _norm_str(v: Any) -> str:
        return str(v or "").strip()

    @staticmethod
    def _ensure_patient_code(patient_code: Any) -> str:
        code = RiwayatPasienService._norm_str(patient_code)
        if not code:
            raise AppError("Kode pasien wajib diisi.", 400)
        return code

    @staticmethod
    def _ensure_patient_exists(patient_code: str) -> Dict:
        row = RiwayatPasienRepository.get_patient_by_code(patient_code)
        if not row:
            raise AppError("Pasien tidak ditemukan.", 404)
        return row

    @staticmethod
    def _group_by_key(rows: List[Dict], key: str) -> Dict[Any, List[Dict]]:
        out: Dict[Any, List[Dict]] = {}
        for row in rows:
            k = row.get(key)
            if k not in out:
                out[k] = []
            out[k].append(row)
        return out

    @staticmethod
    def _split_foto_before_after(rows: List[Dict]) -> Dict[str, List[Dict]]:
        before: List[Dict] = []
        after: List[Dict] = []
        other: List[Dict] = []

        for row in rows:
            jf = RiwayatPasienService._norm_str(row.get("jenis_foto")).lower()
            if jf == "before":
                before.append(row)
            elif jf == "after":
                after.append(row)
            else:
                other.append(row)

        return {
            "before": before,
            "after": after,
            "other": other,
        }

    # =========================
    # PATIENT
    # =========================
    @staticmethod
    def get_patient(patient_code: Any) -> Dict:
        code = RiwayatPasienService._ensure_patient_code(patient_code)
        return RiwayatPasienService._ensure_patient_exists(code)

    # =========================
    # RIWAYAT
    # =========================
    @staticmethod
    def get_riwayat_pasien(patient_code: Any) -> Dict:
        code = RiwayatPasienService._ensure_patient_code(patient_code)
        patient = RiwayatPasienService._ensure_patient_exists(code)

        headers = RiwayatPasienRepository.list_riwayat_headers(code)

        if not headers:
            return {
                "patient": patient,
                "riwayat": []
            }

        diagnosa_ids = [int(x["diagnosa_id"]) for x in headers if x.get("diagnosa_id")]
        pendaftaran_ids = [int(x["pendaftaran_id"]) for x in headers if x.get("pendaftaran_id")]

        detail_rows = RiwayatPasienRepository.list_diagnosa_detail_by_ids(diagnosa_ids)
        foto_rows = RiwayatPasienRepository.list_foto_by_diagnosa_ids(diagnosa_ids)
        treatment_rows = RiwayatPasienRepository.list_treatment_by_pendaftaran_ids(pendaftaran_ids)

        detail_map = RiwayatPasienService._group_by_key(detail_rows, "diagnosa_id")
        foto_map = RiwayatPasienService._group_by_key(foto_rows, "diagnosa_id")
        treatment_map = RiwayatPasienService._group_by_key(treatment_rows, "pendaftaran_id")

        riwayat: List[Dict] = []

        for row in headers:
            diagnosa_id = row["diagnosa_id"]
            pendaftaran_id = row["pendaftaran_id"]

            foto_group = RiwayatPasienService._split_foto_before_after(
                foto_map.get(diagnosa_id, [])
            )

            item = {
                **row,
                "diagnosa_detail": detail_map.get(diagnosa_id, []),
                "treatments": treatment_map.get(pendaftaran_id, []),
                "foto_before": foto_group["before"],
                "foto_after": foto_group["after"],
                "foto_other": foto_group["other"],
                "foto_before_count": len(foto_group["before"]),
                "foto_after_count": len(foto_group["after"]),
            }
            riwayat.append(item)

        return {
            "patient": patient,
            "riwayat": riwayat
        }

    @staticmethod
    def get_riwayat_detail(diagnosa_id: int) -> Dict:
        row = RiwayatPasienRepository.get_riwayat_detail(diagnosa_id)
        if not row:
            raise AppError("Riwayat diagnosa tidak ditemukan.", 404)

        detail_rows = RiwayatPasienRepository.list_diagnosa_detail_by_ids([diagnosa_id])
        foto_rows = RiwayatPasienRepository.list_foto_by_diagnosa_ids([diagnosa_id])
        treatment_rows = RiwayatPasienRepository.list_treatment_by_pendaftaran_ids([row["pendaftaran_id"]])

        foto_group = RiwayatPasienService._split_foto_before_after(foto_rows)

        return {
            **row,
            "diagnosa_detail": detail_rows,
            "treatments": treatment_rows,
            "foto_before": foto_group["before"],
            "foto_after": foto_group["after"],
            "foto_other": foto_group["other"],
        }