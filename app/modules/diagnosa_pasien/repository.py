from typing import Any, Dict, List, Optional

from app.db import get_db


class DiagnosaRepository:

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

    @staticmethod
    def _safe_str(v, default=""):
        try:
            if v is None:
                return default
            return str(v).strip()
        except Exception:
            return default

    # =========================
    # MASTER DIAGNOSA
    # =========================
    @staticmethod
    def list_master_diagnosa(search: str = "", is_active: int = 1, limit: int = 5000) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        try:
            limit_i = int(limit)
        except Exception:
            limit_i = 5000
        limit_i = max(1, min(limit_i, 5000))

        sql = """
        SELECT
            id,
            diagnosa_code,
            diagnosa_name,
            is_active,
            created_at,
            updated_at
        FROM master_diagnosa
        WHERE 1=1
        """
        params: List[Any] = []

        if is_active in (0, 1):
            sql += " AND is_active = %s"
            params.append(is_active)

        if search:
            sql += """
            AND (
                diagnosa_code COLLATE utf8mb4_unicode_ci LIKE %s
                OR diagnosa_name COLLATE utf8mb4_unicode_ci LIKE %s
            )
            """
            s = f"%{search}%"
            params += [s, s]

        sql += " ORDER BY diagnosa_name ASC LIMIT %s"
        params.append(limit_i)

        cur.execute(sql, params)
        return cur.fetchall()

    @staticmethod
    def get_master_diagnosa(master_diagnosa_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            id,
            diagnosa_code,
            diagnosa_name,
            is_active,
            created_at,
            updated_at
        FROM master_diagnosa
        WHERE id = %s
        LIMIT 1
        """
        cur.execute(sql, (master_diagnosa_id,))
        return cur.fetchone()

    # =========================
    # HEADER / LIST
    # =========================
    @staticmethod
    def list_headers_by_pendaftaran(pendaftaran_id: int) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
            SELECT
                d.diagnosa_id,
                d.pendaftaran_id,
                d.dokter_id,
                u_dokter.nama  AS dokter_nama,

                d.tgl_diagnosa,
                d.keluhan_utama,
                d.anamnesis_dokter,
                d.pemeriksaan_fisik,
                d.jenis_kulit,
                d.lokasi_keluhan,
                d.durasi_keluhan,
                d.riwayat_alergi,
                d.riwayat_perawatan,
                d.assessment,
                d.rencana_tindakan,
                d.edukasi_pasien,
                d.saran_kontrol,

                d.created_by,
                u_created.nama AS created_by_nama,
                d.created_at,

                d.updated_by,
                u_updated.nama AS updated_by_nama,
                d.updated_at,

                COALESCE(COUNT(DISTINCT dd.detail_id), 0) AS total_detail,
                COALESCE(COUNT(DISTINCT f.foto_id), 0) AS total_foto

            FROM diagnosa_pasien d
            LEFT JOIN diagnosa_pasien_detail dd
                ON dd.diagnosa_id = d.diagnosa_id
            LEFT JOIN diagnosa_pasien_foto f
                ON f.diagnosa_id = d.diagnosa_id

            LEFT JOIN app_user u_dokter
                ON u_dokter.id = d.dokter_id

            LEFT JOIN app_user u_created
                ON u_created.id = d.created_by

            LEFT JOIN app_user u_updated
                ON u_updated.id = d.updated_by

            WHERE d.pendaftaran_id = %s
            AND COALESCE(d.is_deleted, 0) = 0

            GROUP BY
                d.diagnosa_id,
                d.pendaftaran_id,
                d.dokter_id,
                u_dokter.nama,

                d.tgl_diagnosa,
                d.keluhan_utama,
                d.anamnesis_dokter,
                d.pemeriksaan_fisik,
                d.jenis_kulit,
                d.lokasi_keluhan,
                d.durasi_keluhan,
                d.riwayat_alergi,
                d.riwayat_perawatan,
                d.assessment,
                d.rencana_tindakan,
                d.edukasi_pasien,
                d.saran_kontrol,

                d.created_by,
                u_created.nama,
                d.created_at,

                d.updated_by,
                u_updated.nama,
                d.updated_at

            ORDER BY d.tgl_diagnosa DESC, d.diagnosa_id DESC;
        """
        cur.execute(sql, (pendaftaran_id,))
        return cur.fetchall()

    @staticmethod
    def get_header(diagnosa_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
            SELECT
                d.*,

                COALESCE(u_dokter.nama, '-')  AS dokter_nama,
                COALESCE(u_created.nama, '-') AS created_by_nama,
                COALESCE(u_updated.nama, '-') AS updated_by_nama,

                p.patient_code,
                p.tgl_pendaftaran,
                p.status AS pendaftaran_status,
                p.anamnesis_umum,

                pat.full_name,
                pat.phone,
                pat.birth_date,
                TIMESTAMPDIFF(YEAR, pat.birth_date, DATE(p.tgl_pendaftaran)) AS age_years

            FROM diagnosa_pasien d

            LEFT JOIN app_user u_dokter
                ON u_dokter.id = d.dokter_id

            LEFT JOIN app_user u_created
                ON u_created.id = d.created_by

            LEFT JOIN app_user u_updated
                ON u_updated.id = d.updated_by

            INNER JOIN pendaftaran p
                ON p.pendaftaran_id = d.pendaftaran_id

            LEFT JOIN patient pat
                ON pat.patient_code COLLATE utf8mb4_unicode_ci
                = p.patient_code COLLATE utf8mb4_unicode_ci

            WHERE d.diagnosa_id = %s
            AND COALESCE(d.is_deleted, 0) = 0

            LIMIT 1;
        """
        cur.execute(sql, (diagnosa_id,))
        return cur.fetchone()

    @staticmethod
    def get_header_for_edit(diagnosa_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT *
        FROM diagnosa_pasien
        WHERE diagnosa_id = %s
          AND COALESCE(is_deleted, 0) = 0
        LIMIT 1
        """
        cur.execute(sql, (diagnosa_id,))
        return cur.fetchone()

    @staticmethod
    def get_owner_info(diagnosa_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
            SELECT
                d.diagnosa_id,
                d.created_by,
                u_created.nama AS created_by_nama,

                d.dokter_id,
                u_dokter.nama AS dokter_nama,

                d.pendaftaran_id,
                COALESCE(d.is_deleted, 0) AS is_deleted

            FROM diagnosa_pasien d

            LEFT JOIN app_user u_created
                ON u_created.id = d.created_by

            LEFT JOIN app_user u_dokter
                ON u_dokter.id = d.dokter_id

            WHERE d.diagnosa_id = %s
            LIMIT 1
        """
        cur.execute(sql, (diagnosa_id,))
        return cur.fetchone()

    # =========================
    # INSERT HEADER
    # =========================
    @staticmethod
    def insert_header(data: Dict) -> int:
        db = get_db()
        cur = db.cursor()

        sql = """
        INSERT INTO diagnosa_pasien
        (
            pendaftaran_id,
            dokter_id,
            tgl_diagnosa,
            keluhan_utama,
            anamnesis_dokter,
            pemeriksaan_fisik,
            jenis_kulit,
            lokasi_keluhan,
            durasi_keluhan,
            riwayat_alergi,
            riwayat_perawatan,
            assessment,
            rencana_tindakan,
            edukasi_pasien,
            saran_kontrol,
            created_by,
            updated_by
        )
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cur.execute(
            sql,
            (
                data.get("pendaftaran_id"),
                data.get("dokter_id"),
                data.get("tgl_diagnosa"),
                data.get("keluhan_utama"),
                data.get("anamnesis_dokter"),
                data.get("pemeriksaan_fisik"),
                data.get("jenis_kulit"),
                data.get("lokasi_keluhan"),
                data.get("durasi_keluhan"),
                data.get("riwayat_alergi"),
                data.get("riwayat_perawatan"),
                data.get("assessment"),
                data.get("rencana_tindakan"),
                data.get("edukasi_pasien"),
                data.get("saran_kontrol"),
                data.get("created_by"),
                data.get("updated_by"),
            ),
        )
        db.commit()
        return cur.lastrowid

    # =========================
    # UPDATE HEADER
    # =========================
    @staticmethod
    def update_header(diagnosa_id: int, data: Dict):
        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE diagnosa_pasien
        SET
            dokter_id = %s,
            tgl_diagnosa = %s,
            keluhan_utama = %s,
            anamnesis_dokter = %s,
            pemeriksaan_fisik = %s,
            jenis_kulit = %s,
            lokasi_keluhan = %s,
            durasi_keluhan = %s,
            riwayat_alergi = %s,
            riwayat_perawatan = %s,
            assessment = %s,
            rencana_tindakan = %s,
            edukasi_pasien = %s,
            saran_kontrol = %s,
            updated_by = %s,
            updated_at = NOW()
        WHERE diagnosa_id = %s
          AND COALESCE(is_deleted, 0) = 0
        """

        cur.execute(
            sql,
            (
                data.get("dokter_id"),
                data.get("tgl_diagnosa"),
                data.get("keluhan_utama"),
                data.get("anamnesis_dokter"),
                data.get("pemeriksaan_fisik"),
                data.get("jenis_kulit"),
                data.get("lokasi_keluhan"),
                data.get("durasi_keluhan"),
                data.get("riwayat_alergi"),
                data.get("riwayat_perawatan"),
                data.get("assessment"),
                data.get("rencana_tindakan"),
                data.get("edukasi_pasien"),
                data.get("saran_kontrol"),
                data.get("updated_by"),
                diagnosa_id,
            ),
        )
        db.commit()

    # =========================
    # DELETE / SOFT DELETE
    # =========================
    @staticmethod
    def soft_delete(diagnosa_id: int, deleted_by: int):
        db = get_db()
        cur = db.cursor()

        sql = """
        UPDATE diagnosa_pasien
        SET
            is_deleted = 1,
            deleted_at = NOW(),
            deleted_by = %s,
            updated_at = NOW(),
            updated_by = %s
        WHERE diagnosa_id = %s
          AND COALESCE(is_deleted, 0) = 0
        """
        cur.execute(sql, (deleted_by, deleted_by, diagnosa_id))
        db.commit()

    # =========================
    # DETAILS
    # =========================
    @staticmethod
    def list_details(diagnosa_id: int) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            dd.detail_id,
            dd.diagnosa_id,
            dd.master_diagnosa_id,
            dd.is_primary,
            dd.note,
            dd.created_at,

            md.diagnosa_code,
            md.diagnosa_name
        FROM diagnosa_pasien_detail dd
        INNER JOIN master_diagnosa md
            ON md.id = dd.master_diagnosa_id
        WHERE dd.diagnosa_id = %s
        ORDER BY dd.is_primary DESC, md.diagnosa_name ASC, dd.detail_id ASC
        """
        cur.execute(sql, (diagnosa_id,))
        return cur.fetchall()

    @staticmethod
    def insert_detail(diagnosa_id: int, row: Dict):
        db = get_db()
        cur = db.cursor()

        sql = """
        INSERT INTO diagnosa_pasien_detail
        (
            diagnosa_id,
            master_diagnosa_id,
            is_primary,
            note
        )
        VALUES
        (%s, %s, %s, %s)
        """

        cur.execute(
            sql,
            (
                diagnosa_id,
                row.get("master_diagnosa_id"),
                row.get("is_primary", 0),
                row.get("note"),
            ),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def delete_details_by_diagnosa(diagnosa_id: int):
        db = get_db()
        cur = db.cursor()

        sql = """
        DELETE FROM diagnosa_pasien_detail
        WHERE diagnosa_id = %s
        """
        cur.execute(sql, (diagnosa_id,))
        db.commit()

    @staticmethod
    def replace_details(diagnosa_id: int, details: List[Dict]):
        db = get_db()
        cur = db.cursor()

        try:
            cur.execute(
                "DELETE FROM diagnosa_pasien_detail WHERE diagnosa_id = %s",
                (diagnosa_id,)
            )

            sql_insert = """
            INSERT INTO diagnosa_pasien_detail
            (
                diagnosa_id,
                master_diagnosa_id,
                is_primary,
                note
            )
            VALUES
            (%s, %s, %s, %s)
            """

            for row in details or []:
                cur.execute(
                    sql_insert,
                    (
                        diagnosa_id,
                        row.get("master_diagnosa_id"),
                        row.get("is_primary", 0),
                        row.get("note"),
                    ),
                )

            db.commit()
        except Exception:
            db.rollback()
            raise

    # =========================
    # PHOTOS
    # =========================
    @staticmethod
    def list_photos(diagnosa_id: int) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            foto_id,
            diagnosa_id,
            jenis_foto,
            area_foto,
            file_name,
            file_path,
            taken_at,
            uploaded_by,
            uploaded_at,
            note
        FROM diagnosa_pasien_foto
        WHERE diagnosa_id = %s
        ORDER BY uploaded_at ASC, foto_id ASC
        """
        cur.execute(sql, (diagnosa_id,))
        return cur.fetchall()

    @staticmethod
    def get_photo(foto_id: int) -> Optional[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            foto_id,
            diagnosa_id,
            jenis_foto,
            area_foto,
            file_name,
            file_path,
            taken_at,
            uploaded_by,
            uploaded_at,
            note
        FROM diagnosa_pasien_foto
        WHERE foto_id = %s
        LIMIT 1
        """
        cur.execute(sql, (foto_id,))
        return cur.fetchone()

    @staticmethod
    def insert_photo(diagnosa_id: int, row: Dict):
        db = get_db()
        cur = db.cursor()

        sql = """
        INSERT INTO diagnosa_pasien_foto
        (
            diagnosa_id,
            jenis_foto,
            area_foto,
            file_name,
            file_path,
            taken_at,
            uploaded_by,
            note
        )
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cur.execute(
            sql,
            (
                diagnosa_id,
                row.get("jenis_foto"),
                row.get("area_foto"),
                row.get("file_name"),
                row.get("file_path"),
                row.get("taken_at"),
                row.get("uploaded_by"),
                row.get("note"),
            ),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def delete_photo(foto_id: int):
        db = get_db()
        cur = db.cursor()

        sql = """
        DELETE FROM diagnosa_pasien_foto
        WHERE foto_id = %s
        """
        cur.execute(sql, (foto_id,))
        db.commit()

    # =========================
    # FULL VIEW
    # =========================
    @staticmethod
    def get_full(diagnosa_id: int) -> Optional[Dict]:
        header = DiagnosaRepository.get_header(diagnosa_id)
        if not header:
            return None

        details = DiagnosaRepository.list_details(diagnosa_id)
        photos = DiagnosaRepository.list_photos(diagnosa_id)

        return {
            "header": header,
            "details": details,
            "photos": photos,
        }

    # =========================
    # TRANSACTIONAL HELPERS
    # =========================
    @staticmethod
    def create_full(data: Dict, details: List[Dict], photos: Optional[List[Dict]] = None) -> int:
        db = get_db()
        cur = db.cursor()

        try:
            sql_header = """
            INSERT INTO diagnosa_pasien
            (
                pendaftaran_id,
                dokter_id,
                tgl_diagnosa,
                keluhan_utama,
                anamnesis_dokter,
                pemeriksaan_fisik,
                jenis_kulit,
                lokasi_keluhan,
                durasi_keluhan,
                riwayat_alergi,
                riwayat_perawatan,
                assessment,
                rencana_tindakan,
                edukasi_pasien,
                saran_kontrol,
                created_by,
                updated_by
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(
                sql_header,
                (
                    data.get("pendaftaran_id"),
                    data.get("dokter_id"),
                    data.get("tgl_diagnosa"),
                    data.get("keluhan_utama"),
                    data.get("anamnesis_dokter"),
                    data.get("pemeriksaan_fisik"),
                    data.get("jenis_kulit"),
                    data.get("lokasi_keluhan"),
                    data.get("durasi_keluhan"),
                    data.get("riwayat_alergi"),
                    data.get("riwayat_perawatan"),
                    data.get("assessment"),
                    data.get("rencana_tindakan"),
                    data.get("edukasi_pasien"),
                    data.get("saran_kontrol"),
                    data.get("created_by"),
                    data.get("updated_by"),
                ),
            )
            diagnosa_id = cur.lastrowid

            sql_detail = """
            INSERT INTO diagnosa_pasien_detail
            (
                diagnosa_id,
                master_diagnosa_id,
                is_primary,
                note
            )
            VALUES
            (%s, %s, %s, %s)
            """
            for row in details or []:
                cur.execute(
                    sql_detail,
                    (
                        diagnosa_id,
                        row.get("master_diagnosa_id"),
                        row.get("is_primary", 0),
                        row.get("note"),
                    ),
                )

            if photos:
                sql_photo = """
                INSERT INTO diagnosa_pasien_foto
                (
                    diagnosa_id,
                    jenis_foto,
                    area_foto,
                    file_name,
                    file_path,
                    taken_at,
                    uploaded_by,
                    note
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                for row in photos:
                    cur.execute(
                        sql_photo,
                        (
                            diagnosa_id,
                            row.get("jenis_foto"),
                            row.get("area_foto"),
                            row.get("file_name"),
                            row.get("file_path"),
                            row.get("taken_at"),
                            row.get("uploaded_by"),
                            row.get("note"),
                        ),
                    )

            db.commit()
            return diagnosa_id
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_full(diagnosa_id: int, data: Dict, details: List[Dict]):
        db = get_db()
        cur = db.cursor()

        try:
            sql_update = """
            UPDATE diagnosa_pasien
            SET
                dokter_id = %s,
                tgl_diagnosa = %s,
                keluhan_utama = %s,
                anamnesis_dokter = %s,
                pemeriksaan_fisik = %s,
                jenis_kulit = %s,
                lokasi_keluhan = %s,
                durasi_keluhan = %s,
                riwayat_alergi = %s,
                riwayat_perawatan = %s,
                assessment = %s,
                rencana_tindakan = %s,
                edukasi_pasien = %s,
                saran_kontrol = %s,
                updated_by = %s,
                updated_at = NOW()
            WHERE diagnosa_id = %s
              AND COALESCE(is_deleted, 0) = 0
            """
            cur.execute(
                sql_update,
                (
                    data.get("dokter_id"),
                    data.get("tgl_diagnosa"),
                    data.get("keluhan_utama"),
                    data.get("anamnesis_dokter"),
                    data.get("pemeriksaan_fisik"),
                    data.get("jenis_kulit"),
                    data.get("lokasi_keluhan"),
                    data.get("durasi_keluhan"),
                    data.get("riwayat_alergi"),
                    data.get("riwayat_perawatan"),
                    data.get("assessment"),
                    data.get("rencana_tindakan"),
                    data.get("edukasi_pasien"),
                    data.get("saran_kontrol"),
                    data.get("updated_by"),
                    diagnosa_id,
                ),
            )

            cur.execute(
                "DELETE FROM diagnosa_pasien_detail WHERE diagnosa_id = %s",
                (diagnosa_id,)
            )

            sql_insert_detail = """
            INSERT INTO diagnosa_pasien_detail
            (
                diagnosa_id,
                master_diagnosa_id,
                is_primary,
                note
            )
            VALUES
            (%s, %s, %s, %s)
            """
            for row in details or []:
                cur.execute(
                    sql_insert_detail,
                    (
                        diagnosa_id,
                        row.get("master_diagnosa_id"),
                        row.get("is_primary", 0),
                        row.get("note"),
                    ),
                )

            db.commit()
        except Exception:
            db.rollback()
            raise
    
    @staticmethod
    def get_daily_sales_summary_repo(tanggal: str):
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            COUNT(*) AS total_transaksi,
            COALESCE(SUM(paidAmount), 0) AS total_penerimaan_uang
        FROM pendaftaran
        WHERE LOWER(status) = 'paid'
        AND DATE(tgl_pendaftaran) = %s
        """
        cur.execute(sql, (tanggal,))
        row = cur.fetchone() or {}

        cur.close()
        return row