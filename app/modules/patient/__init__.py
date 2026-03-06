from flask import Blueprint

bp = Blueprint("patient", __name__)

from . import routes