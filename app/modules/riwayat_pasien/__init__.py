from flask import Blueprint

riwayat_pasien_bp = Blueprint(
    "riwayat_pasien",
    __name__,
    template_folder="../../templates"
)

from . import routes  # noqa