from __future__ import annotations

import json
from datetime import date as dt_date
from typing import Any, Dict, List

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    g,
    url_for,
)

from app.common.errors import AppError
from app.common.permission import require_permission
from app.modules.authz.repository import PermissionRepository
from app.modules.diagnosa_pasien.service import DiagnosaService
from ..pendaftaran.repository import PendaftaranRepository

bp = Blueprint("diagnosa_pasien", __name__, url_prefix="/diagnosa-pasien")


# =========================================================
# Helpers
# =========================================================
def _is_json_request() -> bool:
    return request.is_json or request.path.startswith("/api/")


def _parse_json_body() -> Dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise AppError("Payload JSON tidak valid.", 400)
    return data


def _parse_form_int(name: str, default: int = 0) -> int:
    try:
        return int((request.form.get(name) or "").strip())
    except Exception:
        return default


def _parse_form_list(name: str) -> List[Any]:
    """
    Prioritas:
    1. request.form.getlist(name)
    2. request.form.get(name) jika isinya JSON array
    """
    values = request.form.getlist(name)
    if values:
        return values

    raw = (request.form.get(name) or "").strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception:
        return []


def _parse_form_json_list(name: str) -> List[Dict[str, Any]]:
    """
    Mendukung 2 bentuk:
    1. 1 field string JSON array
    2. Multi value list
    """
    raw_items = _parse_form_list(name)
    out: List[Dict[str, Any]] = []

    for item in raw_items:
        if isinstance(item, dict):
            out.append(item)
            continue

        if not isinstance(item, str):
            continue

        item = item.strip()
        if not item:
            continue

        try:
            parsed = json.loads(item)
            if isinstance(parsed, dict):
                out.append(parsed)
            elif isinstance(parsed, list):
                for row in parsed:
                    if isinstance(row, dict):
                        out.append(row)
        except Exception:
            continue

    return out


def _build_payload_from_form(include_pendaftaran_id: bool = False) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}

    if include_pendaftaran_id:
        payload["pendaftaran_id"] = _parse_form_int("pendaftaran_id")

    payload["dokter_id"] = _parse_form_int("dokter_id")
    payload["tgl_diagnosa"] = (request.form.get("tgl_diagnosa") or "").strip()

    payload["keluhan_utama"] = request.form.get("keluhan_utama")
    payload["anamnesis_dokter"] = request.form.get("anamnesis_dokter")
    payload["pemeriksaan_fisik"] = request.form.get("pemeriksaan_fisik")
    payload["jenis_kulit"] = request.form.get("jenis_kulit")
    payload["lokasi_keluhan"] = request.form.get("lokasi_keluhan")
    payload["durasi_keluhan"] = request.form.get("durasi_keluhan")
    payload["riwayat_alergi"] = request.form.get("riwayat_alergi")
    payload["riwayat_perawatan"] = request.form.get("riwayat_perawatan")
    payload["assessment"] = request.form.get("assessment")
    payload["rencana_tindakan"] = request.form.get("rencana_tindakan")
    payload["edukasi_pasien"] = request.form.get("edukasi_pasien")
    payload["saran_kontrol"] = request.form.get("saran_kontrol")

    payload["diagnosa_details"] = _parse_form_json_list("diagnosa_details")
    payload["photos"] = _parse_form_json_list("photos_meta")
    payload["uploaded_files"] = request.files

    return payload


def _json_ok(data: Any = None, message: str = "OK", status: int = 200):
    payload = {"ok": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def _get_current_user_id() -> int | None:
    user_id = None

    if hasattr(g, "user") and isinstance(g.user, dict):
        user_id = g.user.get("id")

    if not user_id:
        user_id = session.get("user_id")

    try:
        user_id = int(user_id)
    except Exception:
        user_id = None

    return user_id if user_id and user_id > 0 else None


def _has_permission(permission_code: str) -> bool:
    if session.get("role") == "admin":
        return True

    user_id = _get_current_user_id()
    if not user_id:
        return False

    try:
        return PermissionRepository.has_permission_user_id(int(user_id), permission_code)
    except Exception:
        return False


# =========================================================
# WEB PAGES
# =========================================================
@bp.route("/pendaftaran/<int:pendaftaran_id>", methods=["GET"])
@require_permission("diagnosa_pasien.view", redirect_on_fail="main.index")
def list_page(pendaftaran_id: int):
    rows = DiagnosaService.list_by_pendaftaran(pendaftaran_id)

    pendaftaran = PendaftaranRepository.get_header(pendaftaran_id)
    if not pendaftaran:
        raise AppError("Data pendaftaran tidak ditemukan.", 404)

    can_create = _has_permission("diagnosa_pasien.create")
    master_diagnosa = []

    if can_create:
        master_diagnosa = DiagnosaService.list_master_diagnosa()

    return render_template(
        "diagnosa_pasien/list.html",
        pendaftaran=pendaftaran,
        rows=rows,
        master_diagnosa=master_diagnosa,
        can_create=can_create,
    )


@bp.route("/list_pasien", methods=["GET"])
@require_permission("diagnosa_pasien.view", redirect_on_fail="main.index")
def list_pasien():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()

    date_str = (request.args.get("date") or "").strip()
    if not date_str:
        date_str = dt_date.today().strftime("%Y-%m-%d")

    rows = PendaftaranRepository.list_headers(search=q, status=status, date=date_str)
    receipt_token = (request.args.get("receipt") or "").strip()

    return render_template(
        "diagnosa_pasien/list_pasien.html",
        rows=rows,
        q=q,
        status=status,
        date=date_str,
        receipt_token=receipt_token,
    )


@bp.route("/list_treatment/<int:pendaftaran_id>/treatment", methods=["GET"])
@require_permission("diagnosa_pasien.view", redirect_on_fail="main.index")
def pendaftaran_treatment_page(pendaftaran_id: int):
    header = PendaftaranRepository.get_header(pendaftaran_id)

    if not header:
        raise AppError("Pendaftaran tidak ditemukan.", 404)

    rows = PendaftaranRepository.list_treatments(pendaftaran_id)

    return render_template(
        "diagnosa_pasien/treatment.html",
        header=header,
        rows=rows,
    )


@bp.route("/create/<int:pendaftaran_id>", methods=["GET"])
@require_permission("diagnosa_pasien.create", redirect_on_fail="main.index")
def create_page(pendaftaran_id: int):
    ctx = DiagnosaService.get_form_context_create(pendaftaran_id)

    return render_template(
        "diagnosa_pasien/form.html",
        mode="create",
        pendaftaran=ctx["pendaftaran"],
        master_diagnosa=ctx["master_diagnosa"],
        data=None,
    )


@bp.route("/create", methods=["POST"])
@require_permission("diagnosa_pasien.create", redirect_on_fail="main.index")
def create_submit():
    payload = _build_payload_from_form(include_pendaftaran_id=True)
    result = DiagnosaService.create(payload)

    flash("Diagnosa berhasil disimpan.", "success")
    return redirect(
        url_for(
            "diagnosa_pasien.view_page",
            diagnosa_id=result["header"]["diagnosa_id"],
        )
    )


@bp.route("/view/<int:diagnosa_id>", methods=["GET"])
@require_permission("diagnosa_pasien.view", redirect_on_fail="main.index")
def view_page(diagnosa_id: int):
    data = DiagnosaService.get_full(diagnosa_id)

    return render_template(
        "diagnosa_pasien/view.html",
        data=data,
    )


@bp.route("/edit/<int:diagnosa_id>", methods=["GET"])
@require_permission("diagnosa_pasien.edit", redirect_on_fail="main.index")
def edit_page(diagnosa_id: int):
    ctx = DiagnosaService.get_form_context_edit(diagnosa_id)

    return render_template(
        "diagnosa_pasien/form.html",
        mode="edit",
        data=ctx["data"],
        master_diagnosa=ctx["master_diagnosa"],
        pendaftaran=ctx["data"]["header"],
    )


@bp.route("/edit/<int:diagnosa_id>", methods=["POST"])
@require_permission("diagnosa_pasien.edit", redirect_on_fail="main.index")
def edit_submit(diagnosa_id: int):
    payload = _build_payload_from_form(include_pendaftaran_id=False)
    result = DiagnosaService.update(diagnosa_id, payload)

    flash("Diagnosa berhasil diperbarui.", "success")
    return redirect(
        url_for(
            "diagnosa_pasien.view_page",
            diagnosa_id=result["header"]["diagnosa_id"],
        )
    )


@bp.route("/delete/<int:diagnosa_id>", methods=["POST"])
@require_permission("diagnosa_pasien.delete", redirect_on_fail="main.index")
def delete_submit(diagnosa_id: int):
    result = DiagnosaService.delete(diagnosa_id)
    flash(result["message"], "success")

    next_url = request.form.get("next") or request.args.get("next")
    if next_url:
        return redirect(next_url)

    return redirect(url_for("main.index"))


@bp.route("/foto/add/<int:diagnosa_id>", methods=["POST"])
@require_permission("diagnosa_pasien.foto_upload", redirect_on_fail="main.index")
def add_photo_submit(diagnosa_id: int):
    """
    Endpoint ini tetap mempertahankan mode lama:
    tambah foto manual dengan field file_name / file_path.
    """
    payload = {
        "jenis_foto": request.form.get("jenis_foto"),
        "area_foto": request.form.get("area_foto"),
        "file_name": request.form.get("file_name"),
        "file_path": request.form.get("file_path"),
        "taken_at": request.form.get("taken_at"),
        "note": request.form.get("note"),
    }

    result = DiagnosaService.add_photo(diagnosa_id, payload)
    flash(result["message"], "success")

    return redirect(url_for("diagnosa_pasien.view_page", diagnosa_id=diagnosa_id))


@bp.route("/foto/delete/<int:foto_id>", methods=["POST"])
@require_permission("diagnosa_pasien.foto_delete", redirect_on_fail="main.index")
def delete_photo_submit(foto_id: int):
    result = DiagnosaService.delete_photo(foto_id)
    flash(result["message"], "success")

    next_url = request.form.get("next") or request.args.get("next")
    if next_url:
        return redirect(next_url)

    return redirect(url_for("main.index"))


@bp.get("/print-daily")
@require_permission("diagnosa_pasien.view")
def pendaftaran_print_daily_page():
    tanggal = (request.args.get("tanggal") or "").strip()

    data = DiagnosaService.get_daily_sales_summary_service(tanggal)

    return render_template(
        "diagnosa_pasien/print_daily.html",
        data=data
    )


# =========================================================
# API
# =========================================================
api = Blueprint("diagnosa_pasien_api", __name__, url_prefix="/api/diagnosa-pasien")


@api.route("/master-diagnosa", methods=["GET"])
@require_permission("diagnosa_pasien.view")
def api_list_master_diagnosa():
    search = (request.args.get("search") or "").strip()
    limit = request.args.get("limit", 5000)

    data = DiagnosaService.list_master_diagnosa(search=search, limit=limit)
    return _json_ok(data=data)


@api.route("/pendaftaran/<int:pendaftaran_id>", methods=["GET"])
@require_permission("diagnosa_pasien.view")
def api_list_by_pendaftaran(pendaftaran_id: int):
    data = DiagnosaService.list_by_pendaftaran(pendaftaran_id)
    return _json_ok(data=data)


@api.route("/form-context/create/<int:pendaftaran_id>", methods=["GET"])
@require_permission("diagnosa_pasien.create")
def api_form_context_create(pendaftaran_id: int):
    data = DiagnosaService.get_form_context_create(pendaftaran_id)
    return _json_ok(data=data)


@api.route("/form-context/edit/<int:diagnosa_id>", methods=["GET"])
@require_permission("diagnosa_pasien.edit")
def api_form_context_edit(diagnosa_id: int):
    data = DiagnosaService.get_form_context_edit(diagnosa_id)
    return _json_ok(data=data)


@api.route("/<int:diagnosa_id>", methods=["GET"])
@require_permission("diagnosa_pasien.view")
def api_get_full(diagnosa_id: int):
    data = DiagnosaService.get_full(diagnosa_id)
    return _json_ok(data=data)


@api.route("", methods=["POST"])
@require_permission("diagnosa_pasien.create")
def api_create():
    payload = _parse_json_body()
    data = DiagnosaService.create(payload)
    return _json_ok(data=data, message="Diagnosa berhasil disimpan.", status=201)


@api.route("/<int:diagnosa_id>", methods=["PUT", "PATCH"])
@require_permission("diagnosa_pasien.edit")
def api_update(diagnosa_id: int):
    payload = _parse_json_body()
    data = DiagnosaService.update(diagnosa_id, payload)
    return _json_ok(data=data, message="Diagnosa berhasil diperbarui.")


@api.route("/<int:diagnosa_id>", methods=["DELETE"])
@require_permission("diagnosa_pasien.delete")
def api_delete(diagnosa_id: int):
    data = DiagnosaService.delete(diagnosa_id)
    return _json_ok(data=data, message=data["message"])


@api.route("/<int:diagnosa_id>/photos", methods=["POST"])
@require_permission("diagnosa_pasien.foto_upload")
def api_add_photo(diagnosa_id: int):
    payload = _parse_json_body()
    data = DiagnosaService.add_photo(diagnosa_id, payload)
    return _json_ok(data=data, message=data["message"], status=201)


@api.route("/photos/<int:foto_id>", methods=["DELETE"])
@require_permission("diagnosa_pasien.foto_delete")
def api_delete_photo(foto_id: int):
    data = DiagnosaService.delete_photo(foto_id)
    return _json_ok(data=data, message=data["message"])


# =========================================================
# Register helper
# =========================================================
def register_blueprints(app):
    app.register_blueprint(bp)
    app.register_blueprint(api)