from flask import request, jsonify, render_template
from . import bp
from .service import TreatmentReportService
from app.common.permission import require_permission


# =========================
# PAGE
# =========================
@bp.get("/reports/treatment")
@require_permission("REPORT.VIEW")
def treatment_page():
    return render_template("report/treatment/index.html")


# =========================
# API
# =========================

@bp.get("")
@require_permission("REPORT.VIEW")
def get_treatment_summary():

    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    data = TreatmentReportService.get_summary(
        start_date=start_date,
        end_date=end_date
    )

    return jsonify({"ok": True, "data": data})


@bp.get("/detail")
@require_permission("REPORT.VIEW")
def get_treatment_detail():

    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    data = TreatmentReportService.get_detail(
        start_date=start_date,
        end_date=end_date
    )

    return jsonify({"ok": True, "data": data})