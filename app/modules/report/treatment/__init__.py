from flask import Blueprint

bp = Blueprint("report_treatment", __name__)

from . import routes