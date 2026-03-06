from functools import wraps
from flask import request, session, g, redirect, url_for, flash
from app.common.errors import AppError
from app.modules.authz.repository import PermissionRepository


def _is_api_request() -> bool:
    return request.path.startswith("/api")


def require_permission(permission_code: str, redirect_on_fail: str | None = None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            # =========================
            # IDENTIFY USER
            # =========================
            user_id = None

            if hasattr(g, "user") and isinstance(g.user, dict):
                user_id = g.user.get("id")

            if not user_id:
                user_id = session.get("user_id")

            # =========================
            # LOGIN CHECK
            # =========================
            if not user_id:
                if _is_api_request():
                    raise AppError("Unauthorized", 401)

                flash("Sesi Anda telah berakhir. Silakan login kembali.", "warning")
                return redirect(url_for("auth.login_page"))

            # =========================
            # ADMIN BYPASS
            # =========================
            if session.get("role") == "admin":
                return fn(*args, **kwargs)

            # =========================
            # PERMISSION CHECK
            # =========================
            ok = PermissionRepository.has_permission_user_id(
                int(user_id),
                permission_code
            )

            if not ok:
                if _is_api_request():
                    raise AppError("FORBIDDEN", 403)

                flash("Anda tidak memiliki hak akses untuk membuka menu ini.", "danger")

                if redirect_on_fail:
                    return redirect(url_for(redirect_on_fail))

                return redirect(url_for("main.index"))

            return fn(*args, **kwargs)

        return wrapper

    return decorator