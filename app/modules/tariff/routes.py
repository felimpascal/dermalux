import os
import uuid

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
)
from werkzeug.utils import secure_filename

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


def _allowed_image(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png"})
    return ext in allowed


def _absolute_static_file_from_db_path(db_path: str | None) -> str | None:
    """
    Convert DB path like 'uploads/tariff/abc.jpg'
    into absolute file path: <app_root>/static/uploads/tariff/abc.jpg
    """
    if not db_path:
        return None

    normalized = str(db_path).replace("\\", "/").strip().lstrip("/")
    return os.path.join(current_app.root_path, "static", normalized)


def _delete_file_if_exists(abs_path: str | None):
    if not abs_path:
        return
    try:
        if os.path.exists(abs_path) and os.path.isfile(abs_path):
            os.remove(abs_path)
    except Exception:
        # sengaja diamkan agar proses utama tidak gagal hanya karena file lama gagal dihapus
        pass


def _save_tariff_image(file_storage):
    """
    Save uploaded tariff image to configured directory.
    Return tuple: (photo_path_for_db, original_filename)
    """
    if not file_storage or not file_storage.filename:
        return None, None

    if not _allowed_image(file_storage.filename):
        raise AppError("File gambar harus berformat JPG, JPEG, atau PNG.", 400)

    mimetype = (file_storage.mimetype or "").lower().strip()
    if mimetype not in ("image/jpeg", "image/png", "image/jpg"):
        raise AppError("Tipe file gambar tidak valid.", 400)

    original_name = secure_filename(file_storage.filename)
    if not original_name:
        raise AppError("Nama file tidak valid.", 400)

    ext = original_name.rsplit(".", 1)[1].lower()
    new_name = f"tariff_{uuid.uuid4().hex}.{ext}"

    upload_dir = current_app.config["UPLOAD_TARIFF_DIR"]
    os.makedirs(upload_dir, exist_ok=True)

    abs_path = os.path.join(upload_dir, new_name)
    file_storage.save(abs_path)

    # path relatif yang disimpan ke DB, untuk dipakai url_for('static', filename=...)
    db_path = f"uploads/tariff/{new_name}"
    return db_path, original_name


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
    category_code = (request.args.get("category") or "").strip().upper()
    category_id = _safe_int(request.args.get("category_id"), None)

    # filter promo category (optional)
    promo_category = (request.args.get("promo_category") or "").strip()

    # pagination optional
    limit = _safe_int(request.args.get("limit"), 500) or 500
    offset = _safe_int(request.args.get("offset"), 0) or 0

    rows = TariffRepository.list_tariffs(
        search=q or None,
        active_only=active_only,
        category_id=category_id,
        category_code=(category_code or None),
        promo_only_today=promo_only_today,
        # aktifkan ini jika repository Anda sudah ditambah param promo_category
        # promo_category=(promo_category or None),
        limit=limit,
        offset=offset,
    )

    categories = TariffRepository.list_categories(active_only=True)
    promo_categories = TariffRepository.list_distinct_promo_categories(active_only=False)

    return render_template(
        "tariff/list.html",
        rows=rows,
        q=q,
        active_only=active_only,
        category=category_code,
        category_id=category_id,
        promo_category=promo_category,
        promo_today=promo_only_today,
        limit=limit,
        offset=offset,
        categories=categories,
        promo_categories=promo_categories,
    )


@tariff_bp.route("/tariff/new", methods=["GET"])
@require_permission("Tariff.Upsert")
def tariff_new_page():
    categories = TariffRepository.list_categories(active_only=True)
    promo_categories = TariffRepository.list_distinct_promo_categories(active_only=False)
    return render_template(
        "tariff/form.html",
        mode="new",
        row=None,
        categories=categories,
        promo_categories=promo_categories,
    )


@tariff_bp.route("/tariff/<int:tariff_id>/edit", methods=["GET"])
@require_permission("Tariff.Upsert")
def tariff_edit_page(tariff_id: int):
    row = TariffRepository.get_by_id(tariff_id)
    if not row:
        raise AppError("Tarif tidak ditemukan.", 404)

    categories = TariffRepository.list_categories(active_only=True)
    promo_categories = TariffRepository.list_distinct_promo_categories(active_only=False)

    return render_template(
        "tariff/form.html",
        mode="edit",
        row=row,
        categories=categories,
        promo_categories=promo_categories,
    )


@tariff_bp.route("/tariff/save", methods=["POST"])
@require_permission("Tariff.Upsert")
def tariff_save_post():
    tariff_id = (request.form.get("id") or "").strip()

    try:
        payload = request.form.to_dict()

        photo = request.files.get("photo")
        if photo and photo.filename:
            # simpan dulu info file lama kalau mode edit
            old_row = None
            old_abs_path = None

            if tariff_id:
                old_row = TariffRepository.get_by_id(int(tariff_id))
                if old_row and old_row.get("photo_path"):
                    old_abs_path = _absolute_static_file_from_db_path(old_row.get("photo_path"))

            # save new file
            photo_path, photo_original_name = _save_tariff_image(photo)
            payload["photo_path"] = photo_path
            payload["photo_original_name"] = photo_original_name

            # update/create data
            if tariff_id:
                TariffService.edit(int(tariff_id), payload)
                # hapus file lama setelah update sukses
                _delete_file_if_exists(old_abs_path)
                flash("Tarif berhasil diperbarui.", "success")
            else:
                TariffService.create(payload)
                flash("Tarif berhasil ditambahkan.", "success")

        else:
            # tanpa upload foto baru
            if tariff_id:
                TariffService.edit(int(tariff_id), payload)
                flash("Tarif berhasil diperbarui.", "success")
            else:
                TariffService.create(payload)
                flash("Tarif berhasil ditambahkan.", "success")

        return redirect(url_for("tariff.tariff_list_page"))

    except AppError as e:
        flash(e.message, "danger")
        if tariff_id:
            return redirect(url_for("tariff.tariff_edit_page", tariff_id=int(tariff_id)))
        return redirect(url_for("tariff.tariff_new_page"))


@tariff_bp.route("/tariff/<int:tariff_id>/photo/delete", methods=["POST"])
@require_permission("Tariff.Upsert")
def tariff_delete_photo_post(tariff_id: int):
    try:
        row = TariffRepository.get_by_id(tariff_id)
        if not row:
            raise AppError("Tarif tidak ditemukan.", 404)

        abs_path = _absolute_static_file_from_db_path(row.get("photo_path"))

        TariffService.edit(
            tariff_id,
            {
                "photo_path": None,
                "photo_original_name": None,
            },
        )

        _delete_file_if_exists(abs_path)

        flash("Foto tarif berhasil dihapus.", "success")
    except AppError as e:
        flash(e.message, "danger")

    return redirect(url_for("tariff.tariff_edit_page", tariff_id=tariff_id))


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
        promo_category = (request.args.get("promo_category") or "").strip()

        limit = _safe_int(request.args.get("limit"), 500) or 500
        offset = _safe_int(request.args.get("offset"), 0) or 0

        rows = TariffRepository.list_tariffs(
            search=q or None,
            active_only=active_only,
            category_id=category_id,
            category_code=(category_code or None),
            promo_only_today=promo_only_today,
            # aktifkan ini jika repository Anda sudah ditambah param promo_category
            # promo_category=(promo_category or None),
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
                "promo_category": promo_category,
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


@tariff_bp.route("/api/tariff/<int:tariff_id>/photo", methods=["POST"])
@require_permission("Tariff.Upsert")
def api_tariff_upload_photo(tariff_id: int):
    try:
        row = TariffRepository.get_by_id(tariff_id)
        if not row:
            raise AppError("Tarif tidak ditemukan.", 404)

        photo = request.files.get("photo")
        if not photo or not photo.filename:
            raise AppError("File foto wajib dipilih.", 400)

        old_abs_path = _absolute_static_file_from_db_path(row.get("photo_path"))

        photo_path, photo_original_name = _save_tariff_image(photo)

        TariffService.edit(
            tariff_id,
            {
                "photo_path": photo_path,
                "photo_original_name": photo_original_name,
            },
        )

        _delete_file_if_exists(old_abs_path)

        return jsonify({
            "ok": True,
            "photo_path": photo_path,
            "photo_original_name": photo_original_name,
        })
    except AppError as e:
        return _json_error(e)


@tariff_bp.route("/api/tariff/<int:tariff_id>/photo", methods=["DELETE"])
@require_permission("Tariff.Upsert")
def api_tariff_delete_photo(tariff_id: int):
    try:
        row = TariffRepository.get_by_id(tariff_id)
        if not row:
            raise AppError("Tarif tidak ditemukan.", 404)

        abs_path = _absolute_static_file_from_db_path(row.get("photo_path"))

        TariffService.edit(
            tariff_id,
            {
                "photo_path": None,
                "photo_original_name": None,
            },
        )

        _delete_file_if_exists(abs_path)

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


@tariff_bp.route("/api/tariff-promo-category", methods=["GET"])
@require_permission("Tariff.View")
def api_tariff_promo_category_list():
    try:
        active_only = (request.args.get("active_only") or "0").strip() == "1"
        rows = TariffRepository.list_distinct_promo_categories(active_only=active_only)
        return jsonify({"ok": True, "data": rows})
    except AppError as e:
        return _json_error(e)