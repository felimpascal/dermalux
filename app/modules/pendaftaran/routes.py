# app/modules/pendaftaran/routes.py

from datetime import date as dt_date

from flask import render_template, request, redirect, url_for, flash, jsonify
from app.common.permission import require_permission
from app.common.errors import AppError

from . import pendaftaran_bp
from .repository import PendaftaranRepository
from .service import PendaftaranService


# =========================
# PAGES
# =========================

@pendaftaran_bp.route("/pendaftaran", methods=["GET"])
@require_permission("Pendaftaran.View")
def pendaftaran_list_page():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()

    date_str = (request.args.get("date") or "").strip()
    if not date_str:
        date_str = dt_date.today().strftime("%Y-%m-%d")

    rows = PendaftaranRepository.list_headers(search=q, status=status, date=date_str)

    receipt_token = (request.args.get("receipt") or "").strip()  # <---

    return render_template(
        "pendaftaran/list.html",
        rows=rows,
        q=q,
        status=status,
        date=date_str,
        receipt_token=receipt_token  # <---
    )

@pendaftaran_bp.route("/pendaftaran/new", methods=["GET"])
@require_permission("Pendaftaran.Upsert")
def pendaftaran_new_page():
    return render_template("pendaftaran/form.html", mode="new", row=None)


@pendaftaran_bp.route("/pendaftaran/<int:pendaftaran_id>/edit", methods=["GET"])
@require_permission("Pendaftaran.View")
def pendaftaran_edit_page(pendaftaran_id: int):

    row = PendaftaranRepository.get_header(pendaftaran_id)

    if not row:
        raise AppError("Pendaftaran tidak ditemukan.", 404)

    return render_template(
        "pendaftaran/form.html",
        mode="edit",
        row=row
    )


@pendaftaran_bp.route("/pendaftaran/save", methods=["POST"])
@require_permission("Pendaftaran.Upsert")
def pendaftaran_save_post():

    pendaftaran_id = (request.form.get("id") or "").strip()

    try:
        if pendaftaran_id:
            PendaftaranService.edit_header(
                int(pendaftaran_id),
                request.form.to_dict()
            )
            flash("Pendaftaran berhasil diperbarui.", "success")

        else:
            PendaftaranService.create_header(
                request.form.to_dict()
            )
            flash("Pendaftaran berhasil dibuat.", "success")

        # balik ke list (default: hari ini)
        return redirect(url_for("pendaftaran.pendaftaran_list_page"))

    except AppError as e:

        flash(e.message, "danger")

        if pendaftaran_id:
            return redirect(
                url_for("pendaftaran.pendaftaran_edit_page", pendaftaran_id=int(pendaftaran_id))
            )

        return redirect(url_for("pendaftaran.pendaftaran_new_page"))


@pendaftaran_bp.route("/pendaftaran/<int:pendaftaran_id>/cancel", methods=["POST"])
@require_permission("Pendaftaran.Upsert")
def pendaftaran_cancel_post(pendaftaran_id: int):
    try:
        PendaftaranService.cancel(pendaftaran_id)
        flash("Pendaftaran berhasil dibatalkan.", "success")
    except AppError as e:
        flash(e.message, "danger")

    return redirect(url_for("pendaftaran.pendaftaran_list_page"))


@pendaftaran_bp.route("/pendaftaran/<int:pendaftaran_id>/confirm", methods=["POST"])
@require_permission("Pendaftaran.Upsert")
def pendaftaran_confirm_post(pendaftaran_id: int):
    try:
        PendaftaranService.confirm(pendaftaran_id)
        flash("Pendaftaran berhasil dikonfirmasi.", "success")
    except AppError as e:
        flash(e.message, "danger")

    return redirect(url_for("diagnosa_pasien.list_pasien"))



# =========================
# TREATMENT PAGE
# =========================

@pendaftaran_bp.route("/pendaftaran/<int:pendaftaran_id>/treatment", methods=["GET"])
@require_permission("Pendaftaran.View")
def pendaftaran_treatment_page(pendaftaran_id: int):

    header = PendaftaranRepository.get_header(pendaftaran_id)

    if not header:
        raise AppError("Pendaftaran tidak ditemukan.", 404)

    rows = PendaftaranRepository.list_treatments(pendaftaran_id)

    return render_template(
        "pendaftaran/treatment.html",
        header=header,
        rows=rows
    )


# =========================
# API
# =========================

@pendaftaran_bp.route("/api/pendaftaran", methods=["GET"])
@require_permission("Pendaftaran.View")
def api_pendaftaran_list():

    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()

    date_str = (request.args.get("date") or "").strip()
    if not date_str:
        date_str = dt_date.today().strftime("%Y-%m-%d")

    rows = PendaftaranRepository.list_headers(
        search=q,
        status=status,
        date=date_str
    )

    return jsonify({"ok": True, "date": date_str, "data": rows})


@pendaftaran_bp.route("/api/pendaftaran/<int:pendaftaran_id>", methods=["GET"])
@require_permission("Pendaftaran.View")
def api_pendaftaran_get(pendaftaran_id: int):

    row = PendaftaranRepository.get_header(pendaftaran_id)

    if not row:
        raise AppError("Pendaftaran tidak ditemukan.", 404)

    return jsonify({"ok": True, "data": row})


# =========================
# API TARIFF (untuk modal DataTables load full)
# =========================

@pendaftaran_bp.route("/api/tariff", methods=["GET"])
@require_permission("Pendaftaran.View")
def api_tariff_list():
    """
    Dipakai oleh modal treatment:
    - load full (limit besar)
    - search client-side oleh DataTables
    Query:
      q     : optional (kalau tetap mau server-side filter)
      limit : default 5000, max 5000
    """
    q = (request.args.get("q") or "").strip()

    try:
        limit = int(request.args.get("limit") or 5000)
    except ValueError:
        limit = 5000
    limit = max(1, min(limit, 5000))

    rows = PendaftaranRepository.list_tariff(search=q, limit=limit)

    return jsonify({"ok": True, "data": rows})


# =========================
# API TREATMENT
# =========================

@pendaftaran_bp.route("/api/pendaftaran/<int:pendaftaran_id>/treatments", methods=["GET"])
@require_permission("Pendaftaran.View")
def api_treatment_list(pendaftaran_id: int):

    rows = PendaftaranRepository.list_treatments(pendaftaran_id)

    return jsonify({"ok": True, "data": rows})


@pendaftaran_bp.route("/api/pendaftaran/<int:pendaftaran_id>/treatments", methods=["POST"])
@require_permission("Pendaftaran.Upsert")
def api_treatment_create(pendaftaran_id: int):
    """
    Body JSON minimal (sesuai frontend terbaru):
      { tariff_id: int, qty: int, notes: str|null }

    Pricing/discount/promo wajib dihitung ulang dari master di backend.
    """
    try:
        payload = request.get_json(silent=True) or {}

        new_id = PendaftaranService.add_treatment(
            pendaftaran_id,
            payload
        )

        return jsonify({"ok": True, "id": new_id})
    except AppError as e:
        return jsonify({"ok": False, "error": e.message}), e.status_code


@pendaftaran_bp.route("/api/pendaftaran/<int:pendaftaran_id>/treatments/<int:detail_id>", methods=["PUT"])
@require_permission("Pendaftaran.Upsert")
def api_treatment_update(pendaftaran_id: int, detail_id: int):
    try:
        payload = request.get_json(silent=True) or {}

        PendaftaranService.update_treatment(
            pendaftaran_id,
            detail_id,
            payload
        )

        return jsonify({"ok": True})
    except AppError as e:
        return jsonify({"ok": False, "error": e.message}), e.status_code


@pendaftaran_bp.route("/api/pendaftaran/<int:pendaftaran_id>/treatments/<int:detail_id>", methods=["DELETE"])
@require_permission("Pendaftaran.Upsert")
def api_treatment_delete(pendaftaran_id: int, detail_id: int):
    try:
        PendaftaranService.delete_treatment(
            pendaftaran_id,
            detail_id
        )

        return jsonify({"ok": True})
    except AppError as e:
        return jsonify({"ok": False, "error": e.message}), e.status_code
    
@pendaftaran_bp.route("/pendaftaran/<int:pendaftaran_id>/paid", methods=["POST"])
@require_permission("Payment.Post")
def pendaftaran_paid_post(pendaftaran_id: int):
    try:
        paid_amount = (request.form.get("paid_amount") or "").strip()
        token = PendaftaranService.paid(pendaftaran_id, paid_amount)

        flash("Pembayaran tersimpan. Receipt siap dibagikan.", "success")
        return redirect(url_for("pendaftaran.pendaftaran_list_page", receipt=token))

    except AppError as e:
        flash(e.message, "danger")
        return redirect(url_for("pendaftaran.pendaftaran_treatment_page", pendaftaran_id=pendaftaran_id))
        
@pendaftaran_bp.route("/r/<token>", methods=["GET"])
def receipt_public_page(token: str):
    token = (token or "").strip()
    if not token:
        raise AppError("Token tidak valid.", 404)

    data = PendaftaranRepository.get_receipt_by_token(token)
    if not data:
        raise AppError("Receipt tidak ditemukan / link tidak valid.", 404)

    header = data["header"]
    details = data["details"]

    total = float(header.get("total") or 0)
    paid = float(header.get("paidAmount") or 0)
    change = paid - total

    return render_template(
        "pendaftaran/receipt_public.html",
        header=header,
        details=details,
        total=total,
        paid=paid,
        change=change
    )

@pendaftaran_bp.route("/pendaftaran/<int:pendaftaran_id>/unset-paid", methods=["POST"])
@require_permission("Payment.Revoke")
def pendaftaran_unset_paid_post(pendaftaran_id: int):
    try:
        PendaftaranService.unset_paid(pendaftaran_id)
        flash("Pembayaran berhasil dibatalkan (unset).", "success")
    except AppError as e:
        flash(e.message, "danger")

    # balik ke list (opsional: pertahankan filter)
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    date_str = (request.args.get("date") or "").strip()

    if q or status or date_str:
        return redirect(url_for("pendaftaran.pendaftaran_list_page", q=q, status=status, date=date_str))

    return redirect(url_for("pendaftaran.pendaftaran_list_page"))