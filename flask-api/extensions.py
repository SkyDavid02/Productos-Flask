import os
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_app(app):
    if not os.path.isabs(app.config["DATABASE"]):
        app.config["DATABASE"] = os.path.join(app.root_path, app.config["DATABASE"])

    database_dir = os.path.dirname(app.config["DATABASE"])

    if database_dir:
        os.makedirs(database_dir, exist_ok=True)

    app.teardown_appcontext(close_db)
