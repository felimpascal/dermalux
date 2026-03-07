from flask import Flask, session, request
from dotenv import load_dotenv
from datetime import timedelta
import os

from app.db import close_db
from app.common.errors import register_error_handlers


def print_routes(app):
    print("\n========== REGISTERED ROUTES ==========")
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        print(f"{methods:10s} {rule.rule:30s} -> {rule.endpoint}")
    print("=======================================\n")


def create_app():
    load_dotenv()

    app = Flask(__name__, template_folder="templates", static_folder="static")

    # =========================
    # BASIC CONFIG
    # =========================
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    app.config["DB_HOST"] = os.getenv("DB_HOST", "127.0.0.1")
    app.config["DB_PORT"] = os.getenv("DB_PORT", "3306")
    app.config["DB_USER"] = os.getenv("DB_USER", "root")
    app.config["DB_PASS"] = os.getenv("DB_PASS", "")
    app.config["DB_NAME"] = os.getenv("DB_NAME", "")

    # =========================
    # SESSION CONFIG (IDLE TIMEOUT)
    # =========================
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "120"))
    )

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SECURE"] = (os.getenv("SESSION_COOKIE_SECURE", "0").strip() == "1")
    app.config["SESSION_REFRESH_EACH_REQUEST"] = True

    # =========================
    # ROLLING SESSION MIDDLEWARE
    # =========================
    @app.before_request
    def refresh_session_expiry():
        if request.path == "/auth/logout_beacon":
            return

        if session.get("user_id"):
            session.permanent = True
            session.modified = True

    # =========================
    # ERROR HANDLER + DB LIFECYCLE
    # =========================
    register_error_handlers(app)
    app.teardown_appcontext(close_db)

    # =========================
    # REGISTER MODULES (BLUEPRINT)
    # =========================
    from app.modules.patient import bp as patient_bp
    from app.modules.auth import bp as auth_bp
    from app.modules.main import bp as main_bp
    from app.modules.user_mgmt import bp as user_mgmt_bp
    from app.modules.tariff import tariff_bp
    from app.modules.diagnosa import diagnosa_bp
    from app.modules.pendaftaran import pendaftaran_bp
    from app.modules.diagnosa_pasien import bp as diagnosa_pasien_bp
    from app.modules.diagnosa_pasien import api as diagnosa_api
    from app.modules.riwayat_pasien import riwayat_pasien_bp as riwayat_bp

    app.register_blueprint(riwayat_bp)
    app.register_blueprint(diagnosa_pasien_bp)
    app.register_blueprint(diagnosa_api)
    app.register_blueprint(pendaftaran_bp)
    app.register_blueprint(diagnosa_bp)
    app.register_blueprint(tariff_bp)
    app.register_blueprint(user_mgmt_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(patient_bp, url_prefix="/api/patients")

    @app.get("/health")
    def health():
        return {"ok": True}

    print_routes(app)
    return app