from flask import Blueprint

pendaftaran_bp = Blueprint("pendaftaran", __name__, template_folder="../../templates")

from . import routes  # noqa