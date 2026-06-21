"""Database adapter — SQLite by default, Supabase (Postgres) when configured.

The rest of the app keeps using SQLite-style `?` placeholders and the
`with get_db() as db: db.execute(...)` pattern. When SUPABASE_DB_URL is set this
module transparently speaks Postgres instead — translating `?` -> `%s`,
`INSERT OR IGNORE` -> `ON CONFLICT DO NOTHING`, and returning rows that support
both `row["col"]` and `row[0]` access (just like sqlite3.Row).

Resilient on serverless (Vercel/Lambda): the filesystem is read-only except
`/tmp`, so SQLite lives under `/tmp` there. If a Postgres URL is set but
unreachable (e.g. an IPv6-only direct host from Vercel), we probe it once at
import and fall back to ephemeral SQLite — the app boots either way and never
500s with FUNCTION_INVOCATION_FAILED.

To go 100% Supabase: set SUPABASE_DB_URL to the **Session pooler** URI
(`...pooler.supabase.com:5432`, IPv4) with the password URL-encoded.
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
from pathlib import Path

log = logging.getLogger("db")


def _default_data_dir() -> str:
    """On serverless only /tmp is writable; locally use ./data."""
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("AWS_REGION"):
        return "/tmp/pencilinsurance"
    return "data"


DATA_DIR = Path(os.getenv("DATA_DIR", _default_data_dir()))
DB_PATH = DATA_DIR / "pencilinsurance.sqlite3"

SUPABASE_DB_URL = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()

_INSERT_OR_IGNORE = re.compile(r"INSERT\s+OR\s+IGNORE\s+INTO", re.IGNORECASE)


def _to_pg(sql: str) -> str:
    """Translate the SQLite SQL dialect used in this app to Postgres."""
    sql = sql.replace("?", "%s")
    if _INSERT_OR_IGNORE.search(sql):
        sql = _INSERT_OR_IGNORE.sub("INSERT INTO", sql)
        if "ON CONFLICT" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return sql


# ── Decide backend: try Postgres once, fall back to SQLite if unreachable ──
_USE_PG = False
_connect_url = ""

if SUPABASE_DB_URL:
    try:
        import psycopg2
        import psycopg2.extras

        _connect_url = SUPABASE_DB_URL
        if "sslmode=" not in _connect_url:
            _connect_url += ("&" if "?" in _connect_url else "?") + "sslmode=require"

        # Probe once so an unreachable host fails fast at import, not per request.
        _probe = psycopg2.connect(_connect_url, connect_timeout=5)
        _probe.close()
        _USE_PG = True
    except Exception as exc:  # noqa: BLE001 — any failure means fall back to SQLite
        log.warning("Postgres unreachable (%s); falling back to SQLite at %s", exc, DB_PATH)
        _USE_PG = False

IS_POSTGRES = _USE_PG


if _USE_PG:

    class _PGCursor:
        def __init__(self, cur):
            self._cur = cur

        def execute(self, sql, params=()):
            self._cur.execute(_to_pg(sql), params)
            return self

        def fetchone(self):
            return self._cur.fetchone()

        def fetchall(self):
            return self._cur.fetchall()

        def __iter__(self):
            return iter(self._cur)

        @property
        def rowcount(self):
            return self._cur.rowcount

    class _PGConnection:
        """Mimics the sqlite3.Connection surface this app relies on."""

        def __init__(self, conn):
            self._conn = conn

        def execute(self, sql, params=()):
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(_to_pg(sql), params)
            return _PGCursor(cur)

        def executescript(self, sql):
            with self._conn.cursor() as cur:
                cur.execute(sql)

        def commit(self):
            self._conn.commit()

        def rollback(self):
            self._conn.rollback()

        def close(self):
            self._conn.close()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self._conn.close()
            return False

    def get_db():
        return _PGConnection(psycopg2.connect(_connect_url))

else:

    def get_db() -> sqlite3.Connection:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection
