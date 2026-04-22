"""
database.py
-----------
SQLite schema + tiny helper layer.

Tables
------
users              : auth + profile (account_type, avg_amount, avg_daily_txns)
emis               : user EMIs (amount + expected week of month)
special_txns       : rare/recurring txns (fees, insurance...)
transactions       : every simulated transaction + risk classification
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "upi.db"


@contextmanager
def get_db():
    """Context manager that yields a sqlite3 connection with row dict access."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT UNIQUE NOT NULL,
                password_hash   TEXT NOT NULL,
                full_name       TEXT,
                account_type    TEXT DEFAULT 'Savings',   -- Savings / Current
                avg_amount      REAL DEFAULT 900.0,        -- ₹ avg per txn
                avg_daily_txns  REAL DEFAULT 3.0,          -- avg # txns / day
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS emis (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                name        TEXT,
                amount      REAL NOT NULL,
                week        INTEGER NOT NULL,    -- 1..5  (week of month)
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS special_txns (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                name            TEXT,
                amount          REAL NOT NULL,
                frequency_months INTEGER NOT NULL,  -- 1=monthly, 3=quarterly...
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                receiver    TEXT,
                amount      REAL NOT NULL,
                ts          TEXT DEFAULT CURRENT_TIMESTAMP,
                risk_score  REAL,
                risk_class  TEXT,        -- Normal / Suspicious / High Risk / Fraud
                action      TEXT,        -- allow / warn / otp / block
                note        TEXT,        -- explanation shown to user
                confirmed   INTEGER DEFAULT 0,   -- 1 = user said "this was me"
                reported    INTEGER DEFAULT 0,   -- 1 = user reported as fraud
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )


# ---------- thin query helpers ----------
def fetch_one(query, params=()):
    with get_db() as c:
        return c.execute(query, params).fetchone()


def fetch_all(query, params=()):
    with get_db() as c:
        return c.execute(query, params).fetchall()


def execute(query, params=()):
    with get_db() as c:
        cur = c.execute(query, params)
        return cur.lastrowid
