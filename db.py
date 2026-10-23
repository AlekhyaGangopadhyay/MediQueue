"""Database connection helpers (plain sqlite3 + hand-written SQL on purpose:
this is a DBMS project, so the SQL is the star, not an ORM)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def connect(path):
    # isolation_level=None -> autocommit mode; we open transactions explicitly with BEGIN.
    conn = sqlite3.connect(path, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite ignores FKs unless this is set per connection
    conn.execute("PRAGMA journal_mode = WAL")  # readers don't block the writer
    return conn


def init_db(conn):
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def transaction(conn):
    """BEGIN IMMEDIATE takes the write lock up-front, so two people booking the same slot
    at the same moment are serialised: the second one sees the first one's row."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
