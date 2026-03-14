from typing import List, Dict
from app.db import get_db


class TreatmentReportRepository:

    @staticmethod
    def get_summary(start_date: str, end_date: str) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            pt.tariff_id,
            pt.tariff_code,
            pt.treatment_name_snapshot,
            COUNT(*) AS total_transaksi,
            SUM(pt.qty) AS total_qty,
            SUM(pt.subtotal) AS total_revenue
        FROM pendaftaran_treatment pt
        INNER JOIN pendaftaran p
            ON p.pendaftaran_id = pt.pendaftaran_id
        WHERE
            p.status = 'PAID'
            AND DATE(p.tgl_pendaftaran) BETWEEN %s AND %s
        GROUP BY
            pt.tariff_id,
            pt.tariff_code,
            pt.treatment_name_snapshot
        ORDER BY
            total_revenue DESC ,
            total_qty DESC
        """

        cur.execute(sql, (start_date, end_date))
        rows = cur.fetchall()
        cur.close()
        return rows


    @staticmethod
    def get_detail(start_date: str, end_date: str) -> List[Dict]:
        db = get_db()
        cur = db.cursor(dictionary=True)

        sql = """
        SELECT
            p.pendaftaran_id,
            p.patient_code,
            DATE(p.tgl_pendaftaran) AS tanggal,
            pt.tariff_code,
            pt.treatment_name_snapshot,
            pt.qty,
            pt.unit_price,
            pt.discount_amount,
            pt.subtotal
        FROM pendaftaran_treatment pt
        INNER JOIN pendaftaran p
            ON p.pendaftaran_id = pt.pendaftaran_id
        WHERE
            p.status = 'PAID'
            AND DATE(p.tgl_pendaftaran) BETWEEN %s AND %s
        ORDER BY
            p.tgl_pendaftaran ASC
        """

        cur.execute(sql, (start_date, end_date))
        rows = cur.fetchall()
        cur.close()
        return rows