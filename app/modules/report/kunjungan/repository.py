from typing import List, Dict
from app.db import get_db


class KunjunganReportRepository:

    @staticmethod
    def get_summary_by_gender_and_age(start_date: str, end_date: str) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            x.kategori_usia,
            SUM(CASE WHEN x.gender = 'M' THEN 1 ELSE 0 END) AS laki_laki,
            SUM(CASE WHEN x.gender = 'F' THEN 1 ELSE 0 END) AS perempuan,
            SUM(CASE WHEN x.gender NOT IN ('M', 'F') OR x.gender IS NULL THEN 1 ELSE 0 END) AS tidak_diketahui,
            COUNT(*) AS total
        FROM (
            SELECT
                pt.gender,
                CASE
                    WHEN pt.birth_date IS NULL THEN 'Tidak diketahui'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 0 AND 5 THEN '0-5'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 6 AND 11 THEN '6-11'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 12 AND 16 THEN '12-16'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 17 AND 25 THEN '17-25'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 26 AND 35 THEN '26-35'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 36 AND 45 THEN '36-45'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 46 AND 55 THEN '46-55'
                    WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) >= 56 THEN '56+'
                    ELSE 'Tidak diketahui'
                END AS kategori_usia
            FROM pendaftaran p
            INNER JOIN patient pt
                ON pt.patient_code = p.patient_code
            WHERE
                p.status = 'paid'
                AND DATE(p.tgl_pendaftaran) BETWEEN %s AND %s
        ) x
        GROUP BY x.kategori_usia
        ORDER BY
            CASE x.kategori_usia
                WHEN '0-5' THEN 1
                WHEN '6-11' THEN 2
                WHEN '12-16' THEN 3
                WHEN '17-25' THEN 4
                WHEN '26-35' THEN 5
                WHEN '36-45' THEN 6
                WHEN '46-55' THEN 7
                WHEN '56+' THEN 8
                ELSE 9
            END
        """

        cur.execute(sql, (start_date, end_date))
        rows = cur.fetchall()
        cur.close()
        return rows

    @staticmethod
    def get_detail_by_gender_and_age(start_date: str, end_date: str) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            p.pendaftaran_id,
            p.patient_code,
            pt.full_name,
            pt.gender,
            pt.birth_date,
            DATE(p.tgl_pendaftaran) AS tanggal_kunjungan,
            TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) AS usia,
            CASE
                WHEN pt.birth_date IS NULL THEN 'Tidak diketahui'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 0 AND 5 THEN '0-5'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 6 AND 11 THEN '6-11'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 12 AND 16 THEN '12-16'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 17 AND 25 THEN '17-25'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 26 AND 35 THEN '26-35'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 36 AND 45 THEN '36-45'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) BETWEEN 46 AND 55 THEN '46-55'
                WHEN TIMESTAMPDIFF(YEAR, pt.birth_date, p.tgl_pendaftaran) >= 56 THEN '56+'
                ELSE 'Tidak diketahui'
            END AS kategori_usia
        FROM pendaftaran p
        INNER JOIN patient pt
            ON pt.patient_code = p.patient_code
        WHERE
            p.status = 'paid'
            AND DATE(p.tgl_pendaftaran) BETWEEN %s AND %s
        ORDER BY p.tgl_pendaftaran ASC, pt.full_name ASC
        """

        cur.execute(sql, (start_date, end_date))
        rows = cur.fetchall()
        cur.close()
        return rows