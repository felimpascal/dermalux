from flask import Blueprint

bp = Blueprint(
    "user_mgmt",
    __name__,
    url_prefix="/users"   # semua route user management di /users
)

from . import routes  # noqa