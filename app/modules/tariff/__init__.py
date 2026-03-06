from flask import Blueprint

tariff_bp = Blueprint("tariff", __name__, template_folder="../../templates")

from . import routes  # noqa