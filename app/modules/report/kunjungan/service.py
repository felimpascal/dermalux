from datetime import datetime
from app.common.errors import AppError
from .repository import KunjunganReportRepository


class KunjunganReportService:

    @staticmethod
    def _norm_str(v) -> str:
        return (v or "").strip()

    @staticmethod
    def _validate_date(date_str: str, field_name: str) -> str:
        value = KunjunganReportService._norm_str(date_str)

        if not value:
            raise AppError(f"{field_name} wajib diisi.", 400)

        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise AppError(f"{field_name} harus berformat YYYY-MM-DD.", 400)

        return value

    @staticmethod
    def _validate_period(start_date: str, end_date: str):
        s = KunjunganReportService._validate_date(start_date, "start_date")
        e = KunjunganReportService._validate_date(end_date, "end_date")

        if s > e:
            raise AppError("start_date tidak boleh lebih besar dari end_date.", 400)

        return s, e

    @staticmethod
    def get_summary(start_date: str, end_date: str):
        s, e = KunjunganReportService._validate_period(start_date, end_date)

        rows = KunjunganReportRepository.get_summary_by_gender_and_age(
            start_date=s,
            end_date=e
        )

        totals = {
            "total_kunjungan": 0,
            "total_laki_laki": 0,
            "total_perempuan": 0,
            "total_tidak_diketahui": 0
        }

        for row in rows:
            totals["total_kunjungan"] += int(row.get("total") or 0)
            totals["total_laki_laki"] += int(row.get("laki_laki") or 0)
            totals["total_perempuan"] += int(row.get("perempuan") or 0)
            totals["total_tidak_diketahui"] += int(row.get("tidak_diketahui") or 0)

        return {
            "start_date": s,
            "end_date": e,
            "totals": totals,
            "rows": rows
        }

    @staticmethod
    def get_detail(start_date: str, end_date: str):
        s, e = KunjunganReportService._validate_period(start_date, end_date)

        rows = KunjunganReportRepository.get_detail_by_gender_and_age(
            start_date=s,
            end_date=e
        )

        return {
            "start_date": s,
            "end_date": e,
            "rows": rows
        }