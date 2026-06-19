"""Database adapter — SQLite by default, Supabase (Postgres) when configured.

The rest of the app keeps using SQLite-style `?` placeholders and the
`with get_db() as db: db.execute(...)` pattern. When SUPABASE_DB_URL is set this
module transparently speaks Postgres instead — translating `?` -> `%s`,
`INSERT OR IGNORE` -> `ON CONFLICT DO NOTHING`, and returning rows that support
both `row["col"]` and `row[0]` access (just like sqlite3.Row).

To go 100% Supabase:
  1. Create a free project at https://supabase.com
  2. Project Settings -> Database -> Connection string -> URI (use the
     "Session"/direct string on port 5432, not the 6543 transaction pooler).
  3. Put it in .env as SUPABASE_DB_URL=postgresql://...:...@...supabase.com:5432/postgres
  4. pip install psycopg2-binary   (run schema_supabase.sql is automatic on boot)
Until that URL is present the app keeps using the local SQLite file, so nothing
breaks while you set the project up.
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DB_PATH = DATA_DIR / "pencilinsurance.sqlite3"

SUPABASE_DB_URL = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
IS_POSTGRES = bool(SUPABASE_DB_URL)

_INSERT_OR_IGNORE = re.compile(r"INSERT\s+OR\s+IGNORE\s+INTO", re.IGNORECASE)


def _to_pg(sql: str) -> str:
    """Translate the SQLite SQL dialect used in this app to Postgres."""
    sql = sql.replace("?", "%s")
    if _INSERT_OR_IGNORE.search(sql):
        sql = _INSERT_OR_IGNORE.sub("INSERT INTO", sql)
        if "ON CONFLICT" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return sql


if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras

    _connect_url = SUPABASE_DB_URL
    if "sslmode=" not in _connect_url:
        _connect_url += ("&" if "?" in _connect_url else "?") + "sslmode=require"

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
