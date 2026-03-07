from flask import request, jsonify, render_template
from . import bp
from .service import KunjunganReportService
from app.common.permission import require_permission


# =========================
# PAGE (HTML)
# =========================
@bp.get("/reports/kunjungan")
#@require_permission("REPORT.KUNJUNGAN.VIEW")
def kunjungan_page():
    return render_template("report/kunjungan/index.html")


# =========================
# API (JSON)
# prefix blueprint Anda misalnya: /api/reports/kunjungan
# =========================

@bp.get("")
#@require_permission("REPORT.KUNJUNGAN.VIEW")
def get_kunjungan_summary():
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    data = KunjunganReportService.get_summary(
        start_date=start_date,
        end_date=end_date
    )
    return jsonify({"ok": True, "data": data})


@bp.get("/detail")
#@require_permission("REPORT.KUNJUNGAN.VIEW")
def get_kunjungan_detail():
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    data = KunjunganReportService.get_detail(
        start_date=start_date,
        end_date=end_date
    )
    return jsonify({"ok": True, "data": data})