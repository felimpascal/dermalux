from flask import render_template, session, redirect, url_for
from . import bp
from flask import render_template
from app.modules.main import bp
from app.common.permission import require_permission
from app.modules.tariff.repository import TariffRepository


@bp.get("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth.login_page"))

    promo_rows = TariffRepository.list_today_active_promos()
    return render_template(
        "index.html",
        title="Dashboard",
        promo_rows=promo_rows
    )

@bp.get("/patients")
@require_permission("PATIENT.VIEW")
def patient_page():
    return render_template("patient/patient.html")

@bp.get("/profile")
def landing_page():
    promo_rows = TariffRepository.list_today_active_promos()

    tariff_rows = TariffRepository.list_tariffs(
        active_only=True,
        limit=100
    )

    return render_template(
        "webprofile/dermalux.html",
        title="Dermalux",
        promo_rows=promo_rows or [],
        tariff_rows=tariff_rows or []
    )
