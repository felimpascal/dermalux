import mysql.connector
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=current_app.config["DB_HOST"],
            port=int(current_app.config["DB_PORT"]),
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASS"],
            database=current_app.config["DB_NAME"],
            autocommit=False,
        )
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()