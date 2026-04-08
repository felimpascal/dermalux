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
from . import team_bp
from .repository import TeamRepository
from .service import TeamService


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
    Convert DB path like 'uploads/team/abc.jpg'
    into absolute file path: <app_root>/static/uploads/team/abc.jpg
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
        pass


def _save_team_image(file_storage):
    """
    Save uploaded team image.
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
    new_name = f"team_{uuid.uuid4().hex}.{ext}"

    upload_dir = current_app.config["UPLOAD_TEAM_DIR"]
    os.makedirs(upload_dir, exist_ok=True)

    abs_path = os.path.join(upload_dir, new_name)
    file_storage.save(abs_path)

    db_path = f"uploads/team/{new_name}"
    return db_path, original_name


# =========================
# PAGES
# =========================

@team_bp.route("/team", methods=["GET"])
@require_permission("Team.View")
def team_list_page():
    q = (request.args.get("q") or "").strip()
    active_only = (request.args.get("active") or "").strip() == "1"

    limit = _safe_int(request.args.get("limit"), 500) or 500
    offset = _safe_int(request.args.get("offset"), 0) or 0

    rows = TeamRepository.list_teams(
        search=q or None,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    return render_template(
        "team/list.html",
        rows=rows,
        q=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@team_bp.route("/team/new", methods=["GET"])
@require_permission("Team.Upsert")
def team_new_page():
    return render_template("team/form.html", mode="new", row=None)


@team_bp.route("/team/<int:team_id>/edit", methods=["GET"])
@require_permission("Team.Upsert")
def team_edit_page(team_id: int):
    row = TeamRepository.get_by_id(team_id)
    if not row:
        raise AppError("Data tim tidak ditemukan.", 404)

    return render_template("team/form.html", mode="edit", row=row)


@team_bp.route("/team/save", methods=["POST"])
@require_permission("Team.Upsert")
def team_save_post():
    team_id = (request.form.get("id") or "").strip()

    try:
        payload = request.form.to_dict()

        photo = request.files.get("photo")
        if photo and photo.filename:
            old_row = None
            old_abs_path = None

            if team_id:
                old_row = TeamRepository.get_by_id(int(team_id))
                if old_row and old_row.get("photo_path"):
                    old_abs_path = _absolute_static_file_from_db_path(old_row.get("photo_path"))

            photo_path, photo_original_name = _save_team_image(photo)
            payload["photo_path"] = photo_path
            payload["photo_original_name"] = photo_original_name

            if team_id:
                TeamService.edit(int(team_id), payload)
                _delete_file_if_exists(old_abs_path)
                flash("Data tim berhasil diperbarui.", "success")
            else:
                TeamService.create(payload)
                flash("Data tim berhasil ditambahkan.", "success")

        else:
            if team_id:
                TeamService.edit(int(team_id), payload)
                flash("Data tim berhasil diperbarui.", "success")
            else:
                TeamService.create(payload)
                flash("Data tim berhasil ditambahkan.", "success")

        return redirect(url_for("team.team_list_page"))

    except AppError as e:
        flash(e.message, "danger")
        if team_id:
            return redirect(url_for("team.team_edit_page", team_id=int(team_id)))
        return redirect(url_for("team.team_new_page"))


@team_bp.route("/team/<int:team_id>/disable", methods=["POST"])
@require_permission("Team.Upsert")
def team_disable_post(team_id: int):
    try:
        TeamService.disable(team_id)
        flash("Data tim berhasil dinonaktifkan.", "success")
    except AppError as e:
        flash(e.message, "danger")
    return redirect(url_for("team.team_list_page"))


@team_bp.route("/team/<int:team_id>/enable", methods=["POST"])
@require_permission("Team.Upsert")
def team_enable_post(team_id: int):
    try:
        TeamService.enable(team_id)
        flash("Data tim berhasil diaktifkan.", "success")
    except AppError as e:
        flash(e.message, "danger")
    return redirect(url_for("team.team_list_page"))


@team_bp.route("/team/<int:team_id>/photo/delete", methods=["POST"])
@require_permission("Team.Upsert")
def team_delete_photo_post(team_id: int):
    try:
        row = TeamRepository.get_by_id(team_id)
        if not row:
            raise AppError("Data tim tidak ditemukan.", 404)

        abs_path = _absolute_static_file_from_db_path(row.get("photo_path"))

        TeamService.edit(
            team_id,
            {
                "photo_path": None,
                "photo_original_name": None,
            },
        )

        _delete_file_if_exists(abs_path)

        flash("Foto tim berhasil dihapus.", "success")
    except AppError as e:
        flash(e.message, "danger")

    return redirect(url_for("team.team_edit_page", team_id=team_id))


# =========================
# API
# =========================

@team_bp.route("/api/team", methods=["GET"])
@require_permission("Team.View")
def api_team_list():
    try:
        q = (request.args.get("q") or "").strip()
        active_only = (request.args.get("active_only") or "0").strip() == "1"

        limit = _safe_int(request.args.get("limit"), 500) or 500
        offset = _safe_int(request.args.get("offset"), 0) or 0

        rows = TeamRepository.list_teams(
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


@team_bp.route("/api/team/public", methods=["GET"])
def api_team_public():
    try:
        limit = _safe_int(request.args.get("limit"), 100) or 100
        rows = TeamRepository.list_public(limit=limit)
        return jsonify({"ok": True, "data": rows})
    except AppError as e:
        return _json_error(e)


@team_bp.route("/api/team/<int:team_id>", methods=["GET"])
@require_permission("Team.View")
def api_team_get(team_id: int):
    try:
        row = TeamRepository.get_by_id(team_id)
        if not row:
            raise AppError("Data tim tidak ditemukan.", 404)
        return jsonify({"ok": True, "data": row})
    except AppError as e:
        return _json_error(e)


@team_bp.route("/api/team", methods=["POST"])
@require_permission("Team.Upsert")
def api_team_create():
    try:
        payload = request.get_json(silent=True) or {}
        new_id = TeamService.create(payload)
        return jsonify({"ok": True, "id": new_id})
    except AppError as e:
        return _json_error(e)


@team_bp.route("/api/team/<int:team_id>", methods=["PATCH"])
@require_permission("Team.Upsert")
def api_team_patch(team_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        TeamService.edit(team_id, payload)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@team_bp.route("/api/team/<int:team_id>/photo", methods=["POST"])
@require_permission("Team.Upsert")
def api_team_upload_photo(team_id: int):
    try:
        row = TeamRepository.get_by_id(team_id)
        if not row:
            raise AppError("Data tim tidak ditemukan.", 404)

        photo = request.files.get("photo")
        if not photo or not photo.filename:
            raise AppError("File foto wajib dipilih.", 400)

        old_abs_path = _absolute_static_file_from_db_path(row.get("photo_path"))
        photo_path, photo_original_name = _save_team_image(photo)

        TeamService.edit(
            team_id,
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


@team_bp.route("/api/team/<int:team_id>/photo", methods=["DELETE"])
@require_permission("Team.Upsert")
def api_team_delete_photo(team_id: int):
    try:
        row = TeamRepository.get_by_id(team_id)
        if not row:
            raise AppError("Data tim tidak ditemukan.", 404)

        abs_path = _absolute_static_file_from_db_path(row.get("photo_path"))

        TeamService.edit(
            team_id,
            {
                "photo_path": None,
                "photo_original_name": None,
            },
        )

        _delete_file_if_exists(abs_path)

        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@team_bp.route("/api/team/<int:team_id>/disable", methods=["PATCH"])
@require_permission("Team.Upsert")
def api_team_disable(team_id: int):
    try:
        TeamService.disable(team_id)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)


@team_bp.route("/api/team/<int:team_id>/enable", methods=["PATCH"])
@require_permission("Team.Upsert")
def api_team_enable(team_id: int):
    try:
        TeamService.enable(team_id)
        return jsonify({"ok": True})
    except AppError as e:
        return _json_error(e)