from flask import Blueprint

bp = Blueprint("report_kunjungan", __name__)

from . import routes