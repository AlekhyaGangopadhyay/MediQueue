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


def ensure_schema(conn, auto_seed=True):
    """Ensures all tables, columns, views, and seed data exist regardless of deployment history."""
    conn.execute("PRAGMA foreign_keys = ON")
    
    # 1. If base database is empty, run full schema
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'patients'").fetchone():
        init_db(conn)
    else:
        # 2. Existing database migration: ensure newer tables exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                room_no       TEXT NOT NULL UNIQUE,
                room_type     TEXT NOT NULL,
                floor         INTEGER,
                status        TEXT NOT NULL DEFAULT 'Available',
                daily_charge  REAL NOT NULL DEFAULT 1000.0,
                dept_id       INTEGER REFERENCES departments(dept_id) ON DELETE SET NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                staff_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name   TEXT NOT NULL,
                role        TEXT NOT NULL,
                phone       TEXT,
                email       TEXT,
                room_id     INTEGER REFERENCES rooms(room_id) ON DELETE SET NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                test_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                test_type TEXT,
                cost      REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                result_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id      INTEGER NOT NULL REFERENCES tests(test_id) ON DELETE RESTRICT,
                patient_id   INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
                result_value TEXT,
                unit         TEXT,
                normal_range TEXT,
                result_date  TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                bill_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id     INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
                bill_date      TEXT NOT NULL,
                total_amount   REAL NOT NULL,
                amount_paid    REAL NOT NULL DEFAULT 0.0,
                payment_status TEXT NOT NULL DEFAULT 'Pending'
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id        INTEGER NOT NULL REFERENCES bills(bill_id) ON DELETE CASCADE,
                payment_date   TEXT NOT NULL,
                amount         REAL NOT NULL,
                payment_mode   TEXT NOT NULL,
                transaction_no TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_bookings (
                booking_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id       INTEGER NOT NULL REFERENCES tests(test_id) ON DELETE RESTRICT,
                patient_id    INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
                booking_date  TEXT NOT NULL,
                slot_time     TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'BOOKED' CHECK (status IN ('BOOKED','COMPLETED','CANCELLED')),
                notes         TEXT,
                created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_bookings_patient ON test_bookings(patient_id, booking_date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_bookings_status ON test_bookings(status);")

        # 3. Missing columns in patients
        patient_cols = [c["name"] for c in conn.execute("PRAGMA table_info(patients)").fetchall()]
        if "address" not in patient_cols:
            conn.execute("ALTER TABLE patients ADD COLUMN address TEXT")
        if "blood_group" not in patient_cols:
            conn.execute("ALTER TABLE patients ADD COLUMN blood_group TEXT")
        if "password_hash" not in patient_cols:
            conn.execute("ALTER TABLE patients ADD COLUMN password_hash TEXT")

        # 4. Missing columns in departments
        dept_cols = [c["name"] for c in conn.execute("PRAGMA table_info(departments)").fetchall()]
        if "location" not in dept_cols:
            conn.execute("ALTER TABLE departments ADD COLUMN location TEXT")
        if "phone" not in dept_cols:
            conn.execute("ALTER TABLE departments ADD COLUMN phone TEXT")

        # 5. Missing columns in consultations
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'consultations'").fetchone():
            consult_cols = [c["name"] for c in conn.execute("PRAGMA table_info(consultations)").fetchall()]
            if "treatment" not in consult_cols:
                conn.execute("ALTER TABLE consultations ADD COLUMN treatment TEXT")
            if "notes" not in consult_cols:
                conn.execute("ALTER TABLE consultations ADD COLUMN notes TEXT")

    # 6. If database has no patients or tests, automatically seed it with full dataset
    if auto_seed:
        patient_count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        test_count = conn.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
        if patient_count == 0 or test_count == 0:
            import seed
            seed.seed(conn)


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
