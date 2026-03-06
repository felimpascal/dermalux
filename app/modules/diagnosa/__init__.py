from flask import Blueprint

diagnosa_bp = Blueprint("diagnosa", __name__, template_folder="../../templates")

from . import routes  # noqa