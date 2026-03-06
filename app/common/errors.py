from flask import jsonify, current_app, request
import os
import traceback

class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def _is_debug_mode() -> bool:
    # Flask debug: app.debug atau env FLASK_DEBUG=1
    # Tambahan custom: APP_DEBUG=1
    return (
        os.getenv("FLASK_DEBUG", "").strip() == "1"
        or os.getenv("APP_DEBUG", "").strip() == "1"
        or getattr(current_app, "debug", False)
    )

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        # tetap log agar keliatan di terminal
        current_app.logger.warning(
            "AppError %s %s -> %s",
            request.method, request.path, err.message
        )
        payload = {"ok": False, "error": err.message}
        if _is_debug_mode():
            payload["type"] = err.__class__.__name__
        return jsonify(payload), err.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        # log lengkap stacktrace ke terminal
        current_app.logger.exception(
            "Unhandled error at %s %s", request.method, request.path
        )

        if _is_debug_mode():
            return jsonify({
                "ok": False,
                "error": str(err),
                "type": err.__class__.__name__,
                "traceback": traceback.format_exc(),
            }), 500

        # production mode: jangan bocorkan detail
        return jsonify({"ok": False, "error": "Internal Server Error"}), 500