from flask import render_template, request, redirect, url_for, flash, jsonify
from app.common.permission import require_permission
from app.common.errors import AppError

from . import diagnosa_bp
from .repository import DiagnosaRepository
from .service import DiagnosaService


# =========================
# PAGES
# =========================

@diagnosa_bp.get("/diagnosa")
@require_permission("Diagnosa.View")
def diagnosa_list_page():
    q = (request.args.get("q") or "").strip()
    active_only = (request.args.get("active") or "").strip() == "1"
    rows = DiagnosaRepository.list_diagnosa(search=q, active_only=active_only)
    return render_template("diagnosa/list.html", title="Master Diagnosa", rows=rows, q=q, active_only=active_only)

@diagnosa_bp.get("/diagnosa/new")
@require_permission("Diagnosa.Upsert")
def diagnosa_new_page():
    return render_template("diagnosa/form.html", title="Tambah Diagnosa", mode="new", row=None)

@diagnosa_bp.get("/diagnosa/<int:diagnosa_id>/edit")
@require_permission("Diagnosa.Upsert")
def diagnosa_edit_page(diagnosa_id: int):
    row = DiagnosaRepository.get_by_id(diagnosa_id)
    if not row:
        raise AppError("Diagnosa tidak ditemukan.", 404)
    return render_template("diagnosa/form.html", title="Edit Diagnosa", mode="edit", row=row)

@diagnosa_bp.post("/diagnosa/save")
@require_permission("Diagnosa.Upsert")
def diagnosa_save_post():
    diagnosa_id = (request.form.get("id") or "").strip()
    try:
        if diagnosa_id:
            DiagnosaService.Upsert(int(diagnosa_id), request.form.to_dict())
            flash("Diagnosa berhasil diperbarui.", "success")
        else:
            DiagnosaService.create(request.form.to_dict())
            flash("Diagnosa berhasil ditambahkan.", "success")
        return redirect(url_for("diagnosa.diagnosa_list_page"))
    except AppError as e:
        flash(e.message, "danger")
        if diagnosa_id:
            return redirect(url_for("diagnosa.diagnosa_edit_page", diagnosa_id=int(diagnosa_id)))
        return redirect(url_for("diagnosa.diagnosa_new_page"))

@diagnosa_bp.post("/diagnosa/<int:diagnosa_id>/disable")
@require_permission("Diagnosa.Upsert")
def diagnosa_disable_post(diagnosa_id: int):
    DiagnosaService.disable(diagnosa_id)
    flash("Diagnosa berhasil dinonaktifkan.", "success")
    return redirect(url_for("diagnosa.diagnosa_list_page"))

@diagnosa_bp.post("/diagnosa/<int:diagnosa_id>/enable")
@require_permission("Diagnosa.Upsert")
def diagnosa_enable_post(diagnosa_id: int):
    DiagnosaService.enable(diagnosa_id)
    flash("Diagnosa berhasil diaktifkan.", "success")
    return redirect(url_for("diagnosa.diagnosa_list_page"))


# =========================
# API (optional)
# =========================

@diagnosa_bp.get("/api/diagnosa")
@require_permission("Diagnosa.View")
def api_diagnosa_list():
    q = (request.args.get("q") or "").strip()
    active_only = (request.args.get("active_only") or "0").strip() == "1"
    rows = DiagnosaRepository.list_diagnosa(search=q, active_only=active_only)
    return jsonify({"ok": True, "data": rows})

@diagnosa_bp.get("/api/diagnosa/<int:diagnosa_id>")
@require_permission("Diagnosa.View")
def api_diagnosa_get(diagnosa_id: int):
    row = DiagnosaRepository.get_by_id(diagnosa_id)
    if not row:
        raise AppError("Diagnosa tidak ditemukan.", 404)
    return jsonify({"ok": True, "data": row})

@diagnosa_bp.post("/api/diagnosa")
@require_permission("Diagnosa.Upsert")
def api_diagnosa_create():
    payload = request.get_json(silent=True) or {}
    new_id = DiagnosaService.create(payload)
    return jsonify({"ok": True, "id": new_id})

@diagnosa_bp.put("/api/diagnosa/<int:diagnosa_id>")
@require_permission("Diagnosa.Upsert")
def api_diagnosa_update(diagnosa_id: int):
    payload = request.get_json(silent=True) or {}
    DiagnosaService.Upsert(diagnosa_id, payload)
    return jsonify({"ok": True})