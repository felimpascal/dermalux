from flask import Blueprint

testimoni_bp = Blueprint("testimoni", __name__, template_folder="../../templates")

from . import routes  # noqa