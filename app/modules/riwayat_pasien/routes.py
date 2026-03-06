# app/modules/riwayat_pasien/routes.py

from flask import render_template, request, jsonify
from app.common.permission import require_permission
from app.common.errors import AppError

from . import riwayat_pasien_bp
from .service import RiwayatPasienService


# =========================
# PAGE
# =========================
@riwayat_pasien_bp.route("/riwayat-pasien", methods=["GET"])
@require_permission("RiwayatPasien.View")
def riwayat_pasien_page():
    patient_code = (request.args.get("patient_code") or "").strip()

    patient = None
    riwayat = []
    error_msg = ""

    if patient_code:
        try:
            data = RiwayatPasienService.get_riwayat_pasien(patient_code)
            patient = data["patient"]
            riwayat = data["riwayat"]
        except AppError as e:
            error_msg = e.message

    return render_template(
        "riwayat_pasien/index.html",
        patient_code=patient_code,
        patient=patient,
        riwayat=riwayat,
        error_msg=error_msg,
    )


# =========================
# API
# =========================
@riwayat_pasien_bp.route("/api/riwayat-pasien/patient", methods=["GET"])
@require_permission("RiwayatPasien.View")
def api_riwayat_pasien_get_patient():
    try:
        patient_code = (request.args.get("patient_code") or "").strip()
        row = RiwayatPasienService.get_patient(patient_code)
        return jsonify({"ok": True, "data": row})
    except AppError as e:
        return jsonify({"ok": False, "error": e.message}), e.status_code


@riwayat_pasien_bp.route("/api/riwayat-pasien", methods=["GET"])
@require_permission("RiwayatPasien.View")
def api_riwayat_pasien_list():
    try:
        patient_code = (request.args.get("patient_code") or "").strip()
        data = RiwayatPasienService.get_riwayat_pasien(patient_code)
        return jsonify({"ok": True, "data": data})
    except AppError as e:
        return jsonify({"ok": False, "error": e.message}), e.status_code


@riwayat_pasien_bp.route("/api/riwayat-pasien/<int:diagnosa_id>", methods=["GET"])
@require_permission("RiwayatPasien.View")
def api_riwayat_pasien_detail(diagnosa_id: int):
    try:
        data = RiwayatPasienService.get_riwayat_detail(diagnosa_id)
        return jsonify({"ok": True, "data": data})
    except AppError as e:
        return jsonify({"ok": False, "error": e.message}), e.status_code