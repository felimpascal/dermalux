from flask import render_template, request, redirect, url_for, flash, jsonify
from app.common.permission import require_permission
from app.common.errors import AppError
from . import tariff_bp
from .repository import TariffRepository
from .service import TariffService


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

@tariff_bp.route("/tariff", methods=["GET"])
@require_permission("Tariff.View")
def tariff_list_page():
    q = (request.args.get("q") or "").strip()
    active_only = (request.args.get("active") or "").strip() == "1"
    promo_only_today = (request.args.get("promo_today") or "").strip() == "1"

    # filter kategori: pilih salah satu
    category_code = (request.args.get("category") or "").strip().upper()  # e.g. FAC/PEEL
    category_id = _safe_int(request.args.get("category_id"), None)

    # pagination optional
    limit = _safe_int(request.args.get("limit"), 500) or 500
    offset = _safe_int(request.args.get("offset"), 0) or 0

    rows = TariffRepository.list_tariffs(
        search=q or None,
        active_only=active_only,
        category_id=category_id,
        category_code=(category_code or None),
        promo_only_today=promo_only_today,
        limit=limit,
        offset=offset,
    )

    # untuk dropdown kategori
    categories = TariffRepository.list_categories(active_only=True)

    return render_template(
        "tariff/list.html",
        rows=rows,
        q=q,
        active_only=active_only,
        category=category_code,         # tetap pakai 'category' karena list.html Anda memakai itu
        category_id=category_id,
        promo_today=promo_only_today,
        limit=limit,
        offset=offset,
        categories=categories,
    )


@tariff_bp.route("/tariff/new", methods=["GET"])
@require_permission("Tariff.Upsert")
def tariff_new_page():
    categories = TariffRepository.list_categories(active_only=True)
    return render_template("tariff/form.html", mode="new", row=None, categories=categories)


@tariff_bp.route("/tariff/<int:tariff_id>/edit", methods=["GET"])
@require_permission("Tariff.Upsert")
def tariff_edit_page(tariff_id: int):
    row = TariffRepository.get_by_id(tariff_id)
    if not row:
        raise AppError("Tarif tidak ditemukan.", 404)
    categories = TariffRepository.list_categories(active_only=True)
    return render_template("tariff/form.html", mode="edit", row=row, categories=categories)


@tariff_bp.route("/tariff/save", methods=["POST"])
@require_permission("Tariff.Upsert")
def tariff_save_post():
    tariff_id = (request.form.get("id") or "").strip()

    try:
        if tariff_id:
            TariffService.edit(int(tariff_id), request.form.to_dict())
            flash("Tarif berhasil diperbarui.", "success")
        else:
            TariffService.create(request.form.to_dict())
            flash("Tarif berhasil ditambahkan.", "success")
        return redirect(url_for("tariff.tariff_list_page"))

    except AppError as e:
        flash(e.message, "danger")
        if tariff_id:
            return redirect(url_for("tariff.tariff_edit_page", tariff_id=int(tariff_id)))
        return redirect(url_for("tariff.tariff_new_page"))


@tariff_bp.route("/tariff/<int:tariff_id>/disable", methods=["POST"])
@require_permission("Tariff.Upsert")
def tariff_disable_post(tariff_id: int):
    try:
        TariffService.disable(tariff_id)
        flash("Tarif berhasil dinonaktifkan.", "success")
    except AppError as e:
        flash(e.message, "danger")
    return redirect(url_for("tariff.tariff_list_page"))


@tariff_bp.route("/tariff/<int:tariff_id>/enable", methods=["POST"])
@require_permission("Tariff.Upsert")
def tariff_enable_post(tariff_id: int):
    try:
        TariffService.enable(tariff_id)
        flash("Tarif berhasil diaktifkan.", "success")
    except AppError as e:
        flash(e.message, "danger")
    return redirect(url_for("tariff.tariff_list_page"))


@tariff_bp.route("/tariff/<int:tariff_id>/promo/disable", methods=["POST"])
@require_permission("Tariff.Upsert")
def tariff_disable_promo_post(tariff_id: int):
    try:
        TariffService.disable_promo(tariff_id)
        flash("Promo berhasil dinonaktifkan.", "success")
    except AppError as e:
        flash(e.message, "danger")
    return redirect(url_for("tariff.tariff_list_page"))


# =========================
# API
# =========================

@tariff_bp.route("/api/tariff", methods=["GET"])
@require_permission("Tariff.View")
def api_tariff_list():
    try:
        q = (request.args.get("q") or "").strip()
        active_only = (request.args.get("active_only") or "0").strip() == "1"
        promo_only_today = (request.args.get("promo_today") or "0").strip() == "1"

        category_code = (request.args.get("category_code") or "").strip().upper()
        category_id = _safe_int(request.args.get("category_id"), None)

        limit = _safe_int(request.args.get("limit"), 500) or 500
        offset = _safe_int(request.args.get("offset"), 0) or 0

        rows = TariffRepository.list_tariffs(
            search=q or None,
            active_only=active_only,
            category_id=category_id,
            category_code=(category_code or None),
            promo_only_today=promo_only_today,
            limit=limit,
            offset=offset,
        )
        return jsonify({
            "ok": True,
            "data": rows,
            "meta": {
                "q": q,
                "active_only": active_only,
                "promo_today": promo_only_today,
                "category_id": category_id,
                "category_code": category_code,
                "limit": limit,
                "offset": offset,
            }
        })
    except AppError as e:
        return _json_error(e)


@tariff_bp.route("/api/tariff/<int:tariff_id>", methods=["GET"])
@require_permission("Tariff.View")
def api_tariff_get(tariff_id: int):
    try:
        row = TariffRepository.get_by_id(tariff_id)
        if not row:
            raise AppError("Tarif tidak ditemukan.", 404)
        return jsonify({"ok": True, "data": row})
    except AppError as e:
        return _json_error(e)


@tariff_bp.route("/api/tariff", methods=["POST"])
@require_permission("Tariff.Upsert")
def api_tariff_create():
    try:
        payload = request.get_json(silent=True) or {}
        new_id = TariffService.create(payload)
        return jsonify({"ok": True, "id": new_id})
    except AppError as e:
        return _json_error(e)


@tariff_bp.route("/api/tariff/<int:tariff_id>", methods=["PATCH"])
@require_permission("Tariff.Upsert")
def api_tariff_patch(tariff_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        TariffService.edit(tariff_id, payload)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@tariff_bp.route("/api/tariff/<int:tariff_id>/disable", methods=["PATCH"])
@require_permission("Tariff.Upsert")
def api_tariff_disable(tariff_id: int):
    try:
        TariffService.disable(tariff_id)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@tariff_bp.route("/api/tariff/<int:tariff_id>/enable", methods=["PATCH"])
@require_permission("Tariff.Upsert")
def api_tariff_enable(tariff_id: int):
    try:
        TariffService.enable(tariff_id)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@tariff_bp.route("/api/tariff/<int:tariff_id>/promo/disable", methods=["PATCH"])
@require_permission("Tariff.Upsert")
def api_tariff_disable_promo(tariff_id: int):
    try:
        TariffService.disable_promo(tariff_id)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)

@tariff_bp.route("/api/tariff/<int:tariff_id>/promo", methods=["PATCH"])
@require_permission("Tariff.Upsert")
def api_tariff_set_promo(tariff_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        TariffService.set_promo(tariff_id, payload)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)

@tariff_bp.route("/api/tariff-category", methods=["GET"])
@require_permission("Tariff.View")
def api_tariff_category_list():
    try:
        active_only = (request.args.get("active_only") or "1").strip() == "1"
        rows = TariffRepository.list_categories(active_only=active_only)
        return jsonify({"ok": True, "data": rows})
    except AppError as e:
        return _json_error(e)