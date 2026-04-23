import sqlite3
import hashlib


def connect():
    conn = sqlite3.connect("pharmacy.db")
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = connect()

    # ============================
    # USERS TABLE
    # ============================
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            username    TEXT     NOT NULL UNIQUE,
            password    TEXT     NOT NULL,
            full_name   TEXT     NOT NULL DEFAULT '',
            role        TEXT     NOT NULL DEFAULT 'pharmacist',
            email       TEXT,
            phone       TEXT,
            is_active   INTEGER  NOT NULL DEFAULT 1,
            created_at  DATETIME DEFAULT (datetime('now','localtime')),
            updated_at  DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)

    # ============================
    # MEDICINES TABLE
    # ============================
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            price         REAL    NOT NULL,
            quantity      INTEGER NOT NULL,
            pharmacy_type TEXT    NOT NULL
        )
    """)

    # ============================
    # DOCTOR ORDERS TABLE
    # ============================
    conn.execute("""
        CREATE TABLE IF NOT EXISTS doctor_orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name    TEXT    NOT NULL,
            patient_id      TEXT    NOT NULL,
            department      TEXT    NOT NULL,
            medicine_name   TEXT    NOT NULL,
            dose            TEXT    NOT NULL,
            notes           TEXT,
            status          TEXT    DEFAULT 'Pending',
            pharmacist_name TEXT,
            dispense_time   TEXT,
            pharmacy_type   TEXT,
            created_at      TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ============================
    # DEFAULT ADMIN USER
    # ============================
    existing = conn.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if not existing:
        conn.execute("""
            INSERT INTO users (username, password, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, ('admin', hash_password('admin1234'), 'System Administrator', 'admin'))

    conn.commit()
    conn.close()