-- Pencil Insurance — Supabase / Postgres schema
-- Applied automatically on boot when SUPABASE_DB_URL is set (see db.py / init_db).
-- You can also paste this into the Supabase SQL editor to provision manually.

CREATE TABLE IF NOT EXISTS profiles (
    id                TEXT PRIMARY KEY,
    auth_provider     TEXT NOT NULL DEFAULT 'guest',
    google_sub        TEXT UNIQUE,
    name              TEXT NOT NULL DEFAULT '',
    email             TEXT NOT NULL DEFAULT '',
    plan              TEXT NOT NULL DEFAULT '',
    school            TEXT NOT NULL DEFAULT '',
    grade             TEXT NOT NULL DEFAULT '',
    avatar_initials   TEXT NOT NULL DEFAULT 'PI',
    avatar_color      TEXT NOT NULL DEFAULT '#d97757',
    avatar_url        TEXT NOT NULL DEFAULT '',
    theme             TEXT NOT NULL DEFAULT 'default',
    role              TEXT NOT NULL DEFAULT 'student',
    created_at        TEXT NOT NULL DEFAULT '',
    updated_at        TEXT NOT NULL DEFAULT '',
    claims_this_cycle INTEGER NOT NULL DEFAULT 0,
    share_token       TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS items (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    price      INTEGER NOT NULL DEFAULT 0,
    category   TEXT NOT NULL DEFAULT 'Misc',
    icon       TEXT NOT NULL DEFAULT '📎',
    plans      TEXT NOT NULL DEFAULT '[]',
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS chat_history (
    id         TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    messages   TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS club_announcements (
    id         BIGSERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    posted_by  TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS club_comments (
    id              BIGSERIAL PRIMARY KEY,
    announcement_id INTEGER NOT NULL,
    user_id         TEXT NOT NULL,
    body            TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS club_members (
    user_id     TEXT PRIMARY KEY,
    approved_by TEXT NOT NULL,
    approved_at TEXT NOT NULL DEFAULT ''
);

-- NEW: membership applications ("apply to join the club")
CREATE TABLE IF NOT EXISTS club_applications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT '',
    name       TEXT NOT NULL DEFAULT '',
    email      TEXT NOT NULL DEFAULT '',
    reason     TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS orders (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    grade         TEXT,
    plan          TEXT,
    location      TEXT,
    notes         TEXT,
    items         TEXT NOT NULL,
    total_price   INTEGER NOT NULL DEFAULT 0,
    covered_value INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS plan_config (
    name        TEXT PRIMARY KEY,
    price       INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    features    TEXT NOT NULL DEFAULT '[]',
    active      INTEGER NOT NULL DEFAULT 1,
    updated_at  TEXT NOT NULL DEFAULT ''
);
