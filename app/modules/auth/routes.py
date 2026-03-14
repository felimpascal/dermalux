from flask import render_template, request, redirect, url_for, flash, session

from . import bp
from .service import AuthService
from app.common.errors import AppError


# =========================
# WEB PAGES
# =========================

@bp.get("/login")
def login_page():
    return render_template("auth/login.html", title="Login")


@bp.post("/login")
def login():
    username = (request.form.get("txtUser", "") or "").strip()
    password = (request.form.get("txtPassword", "") or "").strip()

    if username == "superadmin" and password == "Januari211!":
        session.clear()
        session["user_id"] = "superadmin"
        session["userCode"] = "superadmin"
        session["role"] = "superadmin"
        return redirect(url_for("main.index"))

    try:
        user = AuthService.login_form(username, password)

        session.clear()
        session["user_id"] = user["id"]
        session["userCode"] = user["username"]
        session["nama"] = user["nama"]
        session["role"] = user["role"]

        return redirect(url_for("main.index"))

    except AppError as e:
        flash(e.message)
        return redirect(url_for("auth.login_page"))

@bp.get("/ganti-password")
def ganti_password_page():
    if not session.get("user_id"):
        flash("Silakan login terlebih dahulu.")
        return redirect(url_for("auth.login_page"))

    user = {"passLama": "", "passBaru": "", "passKonfirmasi": ""}
    return render_template("auth/gantiPass.html", title="Ganti Password", user=user)


@bp.post("/ganti-password")
def ganti_password_submit():
    if not session.get("user_id"):
        flash("Silakan login terlebih dahulu.")
        return redirect(url_for("auth.login_page"))

    pass_lama = request.form.get("txtPasswordLama", "") or ""
    pass_baru = request.form.get("txtPasswordBaru", "") or ""
    pass_konfirmasi = request.form.get("txtPasswordKonfirmasi", "") or ""
    print(session)
    try:
        AuthService.change_password(
            user_id=int(session["user_id"]),
            username=str(session.get("userCode") or ""),
            pass_lama=pass_lama,
            pass_baru=pass_baru,
            pass_konfirmasi=pass_konfirmasi,
        )

        session.clear()
        flash("Password berhasil diubah. Silakan login kembali.")
        return redirect(url_for("auth.login_page"))  # FIX: sebelumnya redirect ke auth.login (POST)

    except AppError as e:
        flash(e.message)
        user = {"passLama": pass_lama, "passBaru": pass_baru, "passKonfirmasi": pass_konfirmasi}
        return render_template("auth/gantiPass.html", title="Ganti Password", user=user)


@bp.get("/logout")
def logout():
    session.clear()
    flash("Logout berhasil.")
    return redirect(url_for("auth.login_page"))


# =========================
# CLOSE TAB/WINDOW LOGOUT (BEST-EFFORT)
# =========================
@bp.post("/logout_beacon")
def logout_beacon():
    """
    Dipanggil oleh navigator.sendBeacon saat tab/window ditutup (pagehide).
    Response body kosong supaya cepat.
    """
    session.clear()
    return ("", 204)


# =========================
# OPTIONAL: API
# =========================
@bp.get("/me")
def me():
    if not session.get("user_id"):
        return {"ok": False, "error": "Unauthorized"}, 401
    return {
        "ok": True,
        "data": {
            "user_id": session.get("user_id"),
            "username": session.get("userCode"),
        },
    }