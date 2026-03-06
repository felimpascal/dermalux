from flask import render_template, request, redirect, url_for, flash
from app.common.permission import require_permission
from app.common.errors import AppError
from app.modules.user_mgmt import bp
from app.modules.user_mgmt.service import UserMgmtService


# =========================
# LIST USERS
# =========================
@bp.route("/", methods=["GET"])
@require_permission("user.manage")
def list_users():
    q = (request.args.get("q") or "").strip()

    try:
        rows = UserMgmtService.list_users(q=q)
    except Exception as e:
        flash(f"Gagal mengambil data user: {str(e)}", "danger")
        rows = []

    return render_template(
        "user_mgmt/list.html",
        rows=rows,
        q=q
    )


# =========================
# CREATE USER
# =========================
@bp.route("/new", methods=["GET", "POST"])
@require_permission("user.manage")
def create_user():
    if request.method == "POST":
        try:
            data = {
                "nama": (request.form.get("nama") or "").strip(),
                "username": (request.form.get("username") or "").strip(),
                "role": (request.form.get("role") or "user").strip(),
                "is_active": 1 if request.form.get("is_active") == "1" else 0,
                "password": (request.form.get("password") or "").strip(),
            }

            UserMgmtService.create_user(data)

            flash("User berhasil dibuat.", "success")
            return redirect(url_for("user_mgmt.list_users"))

        except AppError as e:
            flash(str(e), "danger")

        except Exception as e:
            flash(f"Gagal membuat user: {str(e)}", "danger")

        return render_template(
            "user_mgmt/form.html",
            mode="create",
            row=data
        )

    return render_template(
        "user_mgmt/form.html",
        mode="create",
        row=None
    )


# =========================
# EDIT USER
# =========================
@bp.route("/<public_id>/edit", methods=["GET", "POST"])
@require_permission("user.manage")
def edit_user(public_id: str):
    try:
        row = UserMgmtService.get_user_by_public_id(public_id)

        if not row:
            flash("User tidak ditemukan.", "danger")
            return redirect(url_for("user_mgmt.list_users"))

        user_id = row["id"]

    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("user_mgmt.list_users"))

    if request.method == "POST":
        try:
            data = {
                "nama": (request.form.get("nama") or "").strip(),
                "username": (request.form.get("username") or "").strip(),
                "role": (request.form.get("role") or "user").strip(),
                "is_active": 1 if request.form.get("is_active") == "1" else 0,
            }

            UserMgmtService.update_user(user_id, data)

            flash("User berhasil diupdate.", "success")
            return redirect(url_for("user_mgmt.list_users"))

        except AppError as e:
            flash(str(e), "danger")

        except Exception as e:
            flash(f"Gagal update user: {str(e)}", "danger")

        row = {
            "id": user_id,
            "public_id": public_id,
            "nama": data.get("nama", ""),
            "username": data.get("username", ""),
            "role": data.get("role", "user"),
            "is_active": data.get("is_active", 0),
            "created_at": row.get("created_at"),
        }

    return render_template(
        "user_mgmt/form.html",
        mode="edit",
        row=row
    )


# =========================
# RESET PASSWORD
# =========================
@bp.route("/<public_id>/reset-password", methods=["POST"])
@require_permission("user.manage")
def reset_password(public_id: str):
    try:
        user = UserMgmtService.get_user_by_public_id(public_id)
        user_id = user["id"]

        password = (request.form.get("password") or "").strip()

        UserMgmtService.reset_password(user_id, password)

        flash("Password berhasil direset.", "success")

    except AppError as e:
        flash(str(e), "danger")

    except Exception as e:
        flash(f"Gagal reset password: {str(e)}", "danger")

    return redirect(
        url_for("user_mgmt.edit_user", public_id=public_id)
    )


# =========================
# PERMISSION MANAGEMENT
# =========================
@bp.route("/<public_id>/permissions", methods=["GET", "POST"])
@require_permission("user.manage")
def manage_permissions(public_id: str):
    try:
        user = UserMgmtService.get_user_by_public_id(public_id)

        if not user:
            flash("User tidak ditemukan.", "danger")
            return redirect(url_for("user_mgmt.list_users"))

        user_id = user["id"]

    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("user_mgmt.list_users"))

    if request.method == "POST":
        try:
            perm_ids = request.form.getlist("perm_ids")

            UserMgmtService.replace_permissions(user_id, perm_ids)

            flash("Permission berhasil disimpan.", "success")

            return redirect(
                url_for(
                    "user_mgmt.manage_permissions",
                    public_id=public_id
                )
            )

        except Exception as e:
            flash(f"Gagal menyimpan permission: {str(e)}", "danger")

    perms = UserMgmtService.get_permissions_with_granted(user_id)

    return render_template(
        "user_mgmt/permissions.html",
        user=user,
        perms=perms
    )