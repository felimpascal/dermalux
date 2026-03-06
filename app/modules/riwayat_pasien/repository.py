# app/modules/riwayat_pasien/repository.py

from typing import Any, Dict, List, Optional
from app.db import get_db


class RiwayatPasienRepository:

    # =========================
    # Helpers
    # =========================
    @staticmethod
    def _dict_cursor(db):
        return db.cursor(dictionary=True)

    @staticmethod
    def _safe_int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    # =========================
    # PATIENT
    # =========================
    @staticmethod
    def get_patient_by_code(patient_code: str) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
            SELECT
                p.id,
                p.patient_code,
                p.nik,
                p.full_name,
                p.birth_place,
                DATE_FORMAT(p.birth_date, '%d/%m/%Y') AS birth_date,
                p.gender,
                p.phone,
                p.address,
                DATE_FORMAT(p.created_at, '%d/%m/%Y') AS created_at,
                DATE_FORMAT(p.updated_at, '%d/%m/%Y') AS updated_at
            FROM patient p
            WHERE p.patient_code COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
            LIMIT 1;
        """
        cur.execute(sql, (patient_code,))
        return cur.fetchone()

    # =========================
    # RIWAYAT HEADER
    # 1 baris = 1 diagnosa_pasien
    # =========================
    @staticmethod
    def list_riwayat_headers(patient_code: str) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
            SELECT
                dp.diagnosa_id,
                dp.pendaftaran_id,
                pd.patient_code,
                pd.tgl_pendaftaran,
                pd.status AS status_pendaftaran,

                dp.dokter_id,
                dp.tgl_diagnosa,
                dp.keluhan_utama,
                dp.anamnesis_dokter,
                dp.pemeriksaan_fisik,
                dp.jenis_kulit,
                dp.lokasi_keluhan,
                dp.durasi_keluhan,
                dp.riwayat_alergi,
                dp.riwayat_perawatan,
                dp.assessment,
                dp.rencana_tindakan,
                dp.edukasi_pasien,
                dp.saran_kontrol,
                dp.status AS status_diagnosa,

                COALESCE(au.nama, '-') AS dokter_nama

            FROM diagnosa_pasien dp
            INNER JOIN pendaftaran pd
                ON pd.pendaftaran_id = dp.pendaftaran_id
            INNER JOIN patient pt
                ON pt.patient_code COLLATE utf8mb4_unicode_ci
                = pd.patient_code COLLATE utf8mb4_unicode_ci
            LEFT JOIN app_user au
                ON au.id = dp.dokter_id
            WHERE pt.patient_code COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
            AND COALESCE(dp.is_deleted, 0) = 0
            ORDER BY dp.tgl_diagnosa DESC, dp.diagnosa_id DESC;
        """
        cur.execute(sql, (patient_code,))
        return cur.fetchall()

    # =========================
    # DIAGNOSA DETAIL
    # =========================
    @staticmethod
    def list_diagnosa_detail_by_ids(diagnosa_ids: List[int]) -> List[Dict]:
        if not diagnosa_ids:
            return []

        db = get_db()
        cur = db.cursor(dictionary=True)

        placeholders = ",".join(["%s"] * len(diagnosa_ids))
        sql = f"""
        SELECT
            d.detail_id,
            d.diagnosa_id,
            d.master_diagnosa_id,
            d.is_primary,
            d.note,
            md.diagnosa_code,
            md.diagnosa_name
        FROM diagnosa_pasien_detail d
        INNER JOIN master_diagnosa md
            ON md.id = d.master_diagnosa_id
        WHERE d.diagnosa_id IN ({placeholders})
        ORDER BY d.diagnosa_id ASC, d.is_primary DESC, md.diagnosa_name ASC
        """
        cur.execute(sql, tuple(diagnosa_ids))
        return cur.fetchall()

    # =========================
    # FOTO
    # =========================
    @staticmethod
    def list_foto_by_diagnosa_ids(diagnosa_ids: List[int]) -> List[Dict]:
        if not diagnosa_ids:
            return []

        db = get_db()
        cur = db.cursor(dictionary=True)

        placeholders = ",".join(["%s"] * len(diagnosa_ids))
        sql = f"""
        SELECT
            f.foto_id,
            f.diagnosa_id,
            f.jenis_foto,
            f.area_foto,
            f.file_name,
            f.file_path,
            f.taken_at,
            f.uploaded_at,
            f.note,
            u.username AS uploaded_by_name
        FROM diagnosa_pasien_foto f
        LEFT JOIN app_user u
            ON u.id = f.uploaded_by
        WHERE f.diagnosa_id IN ({placeholders})
        ORDER BY
            f.diagnosa_id ASC,
            CASE
                WHEN LOWER(f.jenis_foto) = 'before' THEN 1
                WHEN LOWER(f.jenis_foto) = 'after' THEN 2
                ELSE 3
            END,
            f.foto_id ASC
        """
        cur.execute(sql, tuple(diagnosa_ids))
        return cur.fetchall()

    # =========================
    # TREATMENT
    # =========================
    @staticmethod
    def list_treatment_by_pendaftaran_ids(pendaftaran_ids: List[int]) -> List[Dict]:
        if not pendaftaran_ids:
            return []

        db = get_db()
        cur = db.cursor(dictionary=True)

        placeholders = ",".join(["%s"] * len(pendaftaran_ids))
        sql = f"""
        SELECT
            pt.pendaftaran_treatment_id,
            pt.pendaftaran_id,
            pt.tariff_id,
            pt.tariff_code,
            pt.treatment_name_snapshot,
            pt.qty,
            pt.unit_price,
            pt.discount_type,
            pt.discount_value,
            pt.discount_amount,
            pt.promo_code,
            pt.promo_name,
            pt.subtotal,
            pt.notes,
            pt.sort_no,
            mt.treatment_name,
            mt.category_name
        FROM pendaftaran_treatment pt
        LEFT JOIN master_tariff mt
            ON mt.id = pt.tariff_id
        WHERE pt.pendaftaran_id IN ({placeholders})
        ORDER BY pt.pendaftaran_id ASC, pt.sort_no ASC, pt.pendaftaran_treatment_id ASC
        """
        cur.execute(sql, tuple(pendaftaran_ids))
        return cur.fetchall()

    # =========================
    # DETAIL SINGLE
    # =========================
    @staticmethod
    def get_riwayat_detail(diagnosa_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
            SELECT
                dp.diagnosa_id,
                dp.pendaftaran_id,
                pd.patient_code,
                pd.tgl_pendaftaran,
                pd.status AS status_pendaftaran,

                dp.dokter_id,
                dp.tgl_diagnosa,
                dp.keluhan_utama,
                dp.anamnesis_dokter,
                dp.pemeriksaan_fisik,
                dp.jenis_kulit,
                dp.lokasi_keluhan,
                dp.durasi_keluhan,
                dp.riwayat_alergi,
                dp.riwayat_perawatan,
                dp.assessment,
                dp.rencana_tindakan,
                dp.edukasi_pasien,
                dp.saran_kontrol,
                dp.status AS status_diagnosa,

                COALESCE(au.nama, '-') AS dokter_nama

            FROM diagnosa_pasien dp
            INNER JOIN pendaftaran pd
                ON pd.pendaftaran_id = dp.pendaftaran_id
            LEFT JOIN app_user au
                ON au.id = dp.dokter_id
            WHERE dp.diagnosa_id = %s
            AND COALESCE(dp.is_deleted, 0) = 0
            LIMIT 1;
        """
        cur.execute(sql, (diagnosa_id,))
        return cur.fetchone()