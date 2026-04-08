from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)

from app.common.permission import require_permission
from app.common.errors import AppError
from . import testimoni_bp
from .repository import TestimoniRepository
from .service import TestimoniService


def _json_error(e: AppError):
    return jsonify({"ok": False, "error": e.message}), getattr(e, "status_code", 400)


def _safe_int(x, default=None):
    try:
        if x is None or str(x).strip() == "":
            return default
        return int(str(x).strip())
    except Exception:
        return default


# =========================
# PAGES
# =========================

@testimoni_bp.route("/testimoni", methods=["GET"])
@require_permission("Testimoni.View")
def testimoni_list_page():
    q = (request.args.get("q") or "").strip()
    active_only = (request.args.get("active") or "").strip() == "1"

    limit = _safe_int(request.args.get("limit"), 500) or 500
    offset = _safe_int(request.args.get("offset"), 0) or 0

    rows = TestimoniRepository.list_testimoni(
        search=q or None,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    return render_template(
        "testimoni/list.html",
        rows=rows,
        q=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@testimoni_bp.route("/testimoni/new", methods=["GET"])
@require_permission("Testimoni.Upsert")
def testimoni_new_page():
    return render_template("testimoni/form.html", mode="new", row=None)


@testimoni_bp.route("/testimoni/<int:testimoni_id>/edit", methods=["GET"])
@require_permission("Testimoni.Upsert")
def testimoni_edit_page(testimoni_id: int):
    row = TestimoniRepository.get_by_id(testimoni_id)
    if not row:
        raise AppError("Data testimoni tidak ditemukan.", 404)

    return render_template("testimoni/form.html", mode="edit", row=row)


@testimoni_bp.route("/testimoni/save", methods=["POST"])
@require_permission("Testimoni.Upsert")
def testimoni_save_post():
    testimoni_id = (request.form.get("id") or "").strip()

    try:
        payload = request.form.to_dict()

        if testimoni_id:
            TestimoniService.edit(int(testimoni_id), payload)
            flash("Data testimoni berhasil diperbarui.", "success")
        else:
            TestimoniService.create(payload)
            flash("Data testimoni berhasil ditambahkan.", "success")

        return redirect(url_for("testimoni.testimoni_list_page"))

    except AppError as e:
        flash(e.message, "danger")
        if testimoni_id:
            return redirect(url_for("testimoni.testimoni_edit_page", testimoni_id=int(testimoni_id)))
        return redirect(url_for("testimoni.testimoni_new_page"))


@testimoni_bp.route("/testimoni/<int:testimoni_id>/disable", methods=["POST"])
@require_permission("Testimoni.Upsert")
def testimoni_disable_post(testimoni_id: int):
    try:
        TestimoniService.disable(testimoni_id)
        flash("Data testimoni berhasil dinonaktifkan.", "success")
    except AppError as e:
        flash(e.message, "danger")
    return redirect(url_for("testimoni.testimoni_list_page"))


@testimoni_bp.route("/testimoni/<int:testimoni_id>/enable", methods=["POST"])
@require_permission("Testimoni.Upsert")
def testimoni_enable_post(testimoni_id: int):
    try:
        TestimoniService.enable(testimoni_id)
        flash("Data testimoni berhasil diaktifkan.", "success")
    except AppError as e:
        flash(e.message, "danger")
    return redirect(url_for("testimoni.testimoni_list_page"))


# =========================
# API
# =========================

@testimoni_bp.route("/api/testimoni", methods=["GET"])
@require_permission("Testimoni.View")
def api_testimoni_list():
    try:
        q = (request.args.get("q") or "").strip()
        active_only = (request.args.get("active_only") or "0").strip() == "1"

        limit = _safe_int(request.args.get("limit"), 500) or 500
        offset = _safe_int(request.args.get("offset"), 0) or 0

        rows = TestimoniRepository.list_testimoni(
            search=q or None,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

        return jsonify({
            "ok": True,
            "data": rows,
            "meta": {
                "q": q,
                "active_only": active_only,
                "limit": limit,
                "offset": offset,
            }
        })
    except AppError as e:
        return _json_error(e)


@testimoni_bp.route("/api/testimoni/public", methods=["GET"])
def api_testimoni_public():
    try:
        limit = _safe_int(request.args.get("limit"), 20) or 20
        rows = TestimoniRepository.list_public(limit=limit)
        return jsonify({"ok": True, "data": rows})
    except AppError as e:
        return _json_error(e)


@testimoni_bp.route("/api/testimoni/<int:testimoni_id>", methods=["GET"])
@require_permission("Testimoni.View")
def api_testimoni_get(testimoni_id: int):
    try:
        row = TestimoniRepository.get_by_id(testimoni_id)
        if not row:
            raise AppError("Data testimoni tidak ditemukan.", 404)
        return jsonify({"ok": True, "data": row})
    except AppError as e:
        return _json_error(e)


@testimoni_bp.route("/api/testimoni", methods=["POST"])
@require_permission("Testimoni.Upsert")
def api_testimoni_create():
    try:
        payload = request.get_json(silent=True) or {}
        new_id = TestimoniService.create(payload)
        return jsonify({"ok": True, "id": new_id})
    except AppError as e:
        return _json_error(e)


@testimoni_bp.route("/api/testimoni/<int:testimoni_id>", methods=["PATCH"])
@require_permission("Testimoni.Upsert")
def api_testimoni_patch(testimoni_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        TestimoniService.edit(testimoni_id, payload)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@testimoni_bp.route("/api/testimoni/<int:testimoni_id>/disable", methods=["PATCH"])
@require_permission("Testimoni.Upsert")
def api_testimoni_disable(testimoni_id: int):
    try:
        TestimoniService.disable(testimoni_id)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@testimoni_bp.route("/api/testimoni/<int:testimoni_id>/enable", methods=["PATCH"])
@require_permission("Testimoni.Upsert")
def api_testimoni_enable(testimoni_id: int):
    try:
        TestimoniService.enable(testimoni_id)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)