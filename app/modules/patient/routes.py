from flask import request, jsonify, render_template
from . import bp
from .service import PatientService
from app.common.permission import require_permission


# =========================
# PAGE (HTML)
# =========================
@bp.get("/patients")
@require_permission("PATIENT.VIEW")
def patient_page():
    return render_template("patient/patient.html")


# =========================
# API (JSON)
# prefix blueprint Anda: /api/patients
# =========================

@bp.post("")
@require_permission("PATIENT.UPSERT")
def create_patient():
    payload = request.get_json(silent=True) or {}
    data = PatientService.create(payload)
    return jsonify({"ok": True, "data": data}), 201


@bp.get("")
@require_permission("PATIENT.VIEW")
def search_patient():
    q = (request.args.get("q") or "").strip()
    limit = request.args.get("limit") or "50"
    data = PatientService.search(q=q, limit=limit)
    return jsonify({"ok": True, "data": data})


@bp.get("/<int:patient_id>")
@require_permission("PATIENT.VIEW")
def get_patient(patient_id: int):
    data = PatientService.get(patient_id)
    return jsonify({"ok": True, "data": data})


@bp.put("/<int:patient_id>")
@require_permission("PATIENT.UPSERT")
def update_patient(patient_id: int):
    payload = request.get_json(silent=True) or {}
    data = PatientService.update(patient_id, payload)
    return jsonify({"ok": True, "data": data})


# =========================
# OPTIONAL: for Pendaftaran (fetch by patient_code)
# =========================
@bp.get("/by-code/<patient_code>")
@require_permission("PATIENT.VIEW")
def get_patient_by_code(patient_code: str):
    data = PatientService.get_by_code(patient_code)
    return jsonify({"ok": True, "data": data})