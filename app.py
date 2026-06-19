import os
import re
import secrets
import sqlite3
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

# Database adapter: SQLite locally, Supabase/Postgres when SUPABASE_DB_URL is set.
from db import get_db, IS_POSTGRES  # noqa: E402  (must follow load_dotenv)

app = Flask(__name__)

# ─── Environment mode ─────────────────────────────────────
DEBUG = os.getenv("FLASK_DEBUG") == "1"
IS_PRODUCTION = not DEBUG

# ─── Secret key (no insecure default in production) ───────
_secret = os.getenv("SECRET_KEY", "").strip()
if not _secret:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    # Dev only: ephemeral key (sessions reset on restart) + loud warning.
    _secret = secrets.token_urlsafe(48)
    app.logger.warning("SECRET_KEY not set — using an ephemeral dev key. Set SECRET_KEY before deploying.")
app.secret_key = _secret

# ─── Hardened session / cookie configuration ──────────────
app.config.update(
    SEND_FILE_MAX_AGE_DEFAULT=0,
    SESSION_COOKIE_HTTPONLY=True,          # JS cannot read the session cookie
    SESSION_COOKIE_SAMESITE="Lax",         # blocks cross-site cookie sending (CSRF defense)
    SESSION_COOKIE_SECURE=IS_PRODUCTION,   # HTTPS-only cookie in production
    SESSION_COOKIE_NAME="__Host-pi_session" if IS_PRODUCTION else "pi_session",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_REFRESH_EACH_REQUEST=True,
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,    # reject request bodies > 8 MB (DoS guard)
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DB_PATH = DATA_DIR / "pencilinsurance.sqlite3"

# ─── CORS: never wildcard. Cross-origin only when explicitly allowed. ───
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGIN", "").split(",") if o.strip()]
if ALLOWED_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)
# When unset, no CORS headers are added — same-origin requests still work normally.

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["600 per hour", "120 per minute"],  # baseline abuse guard
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)

@limiter.request_filter
def _exempt_static_from_limits():
    # Don't rate-limit static asset requests (CSS/JS/images) — only dynamic routes.
    return request.path.startswith("/static/")

@app.before_request
def _make_session_permanent():
    session.permanent = True

# ─── CSRF protection (origin/referer verification) ────────
# State-changing /api/* requests must originate from this site. Combined with
# SameSite=Lax cookies this blocks cross-site request forgery without requiring
# any frontend token plumbing (the existing JSON fetch calls are same-origin).
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

def _request_origin_ok() -> bool:
    origin = request.headers.get("Origin")
    if origin:
        if urlparse(origin).netloc == request.host:
            return True
        return origin in ALLOWED_ORIGINS
    referer = request.headers.get("Referer")
    if referer:
        if urlparse(referer).netloc == request.host:
            return True
        return any(referer.startswith(o) for o in ALLOWED_ORIGINS)
    return False  # mutating request with neither Origin nor Referer → reject

@app.before_request
def _csrf_protect():
    if request.method in SAFE_METHODS:
        return None
    if not request.path.startswith("/api/"):
        return None
    if not _request_origin_ok():
        return jsonify({"error": "Cross-origin request blocked"}), 403
    return None

# ─── Security response headers ────────────────────────────
# CSP tuned to the exact external origins this app uses:
#   Google Fonts, cdnjs, Google Sign-In (accounts/gstatic/googleusercontent),
#   Unsplash (Netflix-theme hero), Formspree. 'unsafe-inline' is required because
#   the templates rely on inline <style>/<script> and inline event handlers.
_CSP_DIRECTIVES = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com https://www.gstatic.com https://cdnjs.cloudflare.com",
    "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
    "font-src": "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:",
    "img-src": "'self' data: blob: https://images.unsplash.com https://*.gstatic.com https://*.googleusercontent.com",
    "connect-src": "'self' https://accounts.google.com https://formspree.io",
    "frame-src": "https://accounts.google.com https://content.googleapis.com",
    "media-src": "'self' blob:",        # scanner camera stream
    "worker-src": "'self' blob:",
    "object-src": "'none'",
    "base-uri": "'self'",
    "form-action": "'self' https://formspree.io",
    "frame-ancestors": "'none'",        # clickjacking protection
}

def _build_csp() -> str:
    directives = dict(_CSP_DIRECTIVES)
    if ALLOWED_ORIGINS:
        directives["connect-src"] += " " + " ".join(ALLOWED_ORIGINS)
    policy = "; ".join(f"{k} {v}" for k, v in directives.items())
    if IS_PRODUCTION:
        policy += "; upgrade-insecure-requests"
    return policy

_CSP_VALUE = _build_csp()

@app.after_request
def _set_security_headers(response):
    response.headers["Content-Security-Policy"] = _CSP_VALUE
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(self), microphone=(), geolocation=(), browsing-topics=(), interest-cohort=()"
    )
    # Google Sign-In opens popups and needs window.opener access.
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["X-XSS-Protection"] = "0"  # modern browsers; disable buggy legacy auditor
    response.headers["Server"] = "pencil-insurance"  # reduce version fingerprinting
    # HSTS only over HTTPS / in production (honors reverse-proxy header).
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if IS_PRODUCTION and (request.is_secure or forwarded_proto == "https"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response

# ---------- Gemini setup ----------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
gemini_model = None
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    except Exception:
        pass

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
MAX_MESSAGES = 10
MAX_MESSAGE_LENGTH = 500
VALID_ROLES = {"user", "assistant"}
VALID_PLANS = {"", "Default", "Deluxe", "Ultra", "Efficiency", "Not sure yet"}
VALID_THEMES = {"default", "terminal", "claude", "neon", "sakura", "ocean", "glass", "google", "netflix"}
PLAN_ORDER = ("Default", "Deluxe", "Ultra", "Efficiency")
VALID_ORDER_STATUSES = {"pending", "confirmed", "delivered", "cancelled"}
ORDER_STATUS_ALIASES = {"processing": "confirmed", "fulfilled": "delivered"}
ADMIN_EMAIL = "pencil.insurance.buisness@gmail.com"
CONTACT_EMAIL = "pencil.insurance.buisness@gmail.com"
WHATSAPP = "9901126174"

# ---------- System prompt (from file) ----------
SYSTEM_PROMPT_FILE = Path("prompts/system_prompt.txt")
if SYSTEM_PROMPT_FILE.exists():
    SYSTEM_PROMPT = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
else:
    SYSTEM_PROMPT = "You are PencilBot, the official Pencil Insurance assistant. Only answer questions about Pencil Insurance plans, claims, and school stationery."

PLAN_SUMMARIES = {
    "Default": "Default covers a pencil, sharpener, eraser, and a Butterflow pen.",
    "Deluxe": "Deluxe includes everything in Default, plus Octane pens, protector and compass, divider and pouch, mechanical pencil, and scale.",
    "Ultra": "Ultra includes Deluxe coverage, plus notebooks, branded stationery, markers, colored pencils, refills, and 10 sheets of paper weekly.",
    "Efficiency": "Efficiency includes Ultra coverage, 50 sheets of paper, premium notebooks, stationery up to ₹900, priority support, and art supplies.",
}

submissions: list[dict[str, str]] = []

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def clean_text(value: Any, max_length: int | None = MAX_MESSAGE_LENGTH) -> str:
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    cleaned = normalized.strip()
    return cleaned[:max_length] if max_length else cleaned

def init_db() -> None:
    # Supabase/Postgres: provision from schema_supabase.sql and stop here.
    if IS_POSTGRES:
        schema = (Path(__file__).parent / "schema_supabase.sql").read_text(encoding="utf-8")
        with get_db() as db:
            db.executescript(schema)
            db.commit()
        seed_plans()
        seed_items()
        return
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                auth_provider TEXT NOT NULL DEFAULT 'guest',
                google_sub TEXT UNIQUE,
                name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                plan TEXT NOT NULL DEFAULT '',
                school TEXT NOT NULL DEFAULT '',
                grade TEXT NOT NULL DEFAULT '',
                avatar_initials TEXT NOT NULL DEFAULT 'PI',
                avatar_color TEXT NOT NULL DEFAULT '#e8c84a',
                avatar_url TEXT NOT NULL DEFAULT '',
                theme TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL DEFAULT 'student',
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT '',
                claims_this_cycle INTEGER NOT NULL DEFAULT 0,
                share_token TEXT UNIQUE
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'Misc',
                icon TEXT NOT NULL DEFAULT '📎',
                plans TEXT NOT NULL DEFAULT '[]',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                messages TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS club_announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                posted_by TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT ''
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS club_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                announcement_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(announcement_id) REFERENCES club_announcements(id),
                FOREIGN KEY(user_id) REFERENCES profiles(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS club_members (
                user_id TEXT PRIMARY KEY,
                approved_by TEXT NOT NULL,
                approved_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES profiles(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS club_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT ''
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                grade TEXT,
                plan TEXT,
                location TEXT,
                notes TEXT,
                items TEXT NOT NULL,
                total_price INTEGER NOT NULL DEFAULT 0,
                covered_value INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT ''
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS plan_config (
                name TEXT PRIMARY KEY,
                price INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                features TEXT NOT NULL DEFAULT '[]',
                active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT ''
            )
        """)
        existing = {row["name"] for row in db.execute("PRAGMA table_info(profiles)").fetchall()}
        if "role" not in existing:
            db.execute("ALTER TABLE profiles ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
        if "claims_this_cycle" not in existing:
            db.execute("ALTER TABLE profiles ADD COLUMN claims_this_cycle INTEGER NOT NULL DEFAULT 0")
        if "share_token" not in existing:
            db.execute("ALTER TABLE profiles ADD COLUMN share_token TEXT UNIQUE")
        db.commit()
    seed_plans()
    seed_items()

def seed_plans():
    with get_db() as db:
        defaults = [
            ("Default", 60, "Basic stationery coverage", '["Pencil","Eraser","Sharpener","Pen (Butterflow)"]'),
            ("Deluxe", 100, "Everything in Default plus geometry tools", '["Everything in Default","Compass","Scale","Mechanical Pencil","Divider","Pouch"]'),
            ("Ultra", 200, "Deluxe plus notebooks and art supplies", '["Everything in Deluxe","Notebooks","Markers","Colored Pencils","Highlighters","Refills"]'),
            ("Efficiency", 1000, "Full coverage including premium items", '["Everything in Ultra","Art supplies","Premium notebooks","Any item up to ₹900","Priority support"]'),
        ]
        ts = now_iso()
        for name, price, desc, feats in defaults:
            db.execute(
                "INSERT OR IGNORE INTO plan_config (name,price,description,features,active,updated_at) VALUES (?,?,?,?,1,?)",
                (name, price, desc, feats, ts)
            )
        db.commit()

def plan_names_from_catalog_item(name: str, category: str, price: int) -> list[str]:
    text = f"{name} {category}".lower()
    plans: set[str] = set()

    def include_from(plan: str) -> None:
        if plan in PLAN_ORDER:
            start = PLAN_ORDER.index(plan)
            plans.update(PLAN_ORDER[start:])

    basic_pencil = "pencil" in text and not any(word in text for word in ("mechanical", "color", "colour", "sketch", "charcoal", "case", "lead", "box", "set"))
    basic_eraser = "eraser" in text and not any(word in text for word in ("pack", "refill"))
    basic_sharpener = "sharpener" in text and "electric" not in text
    butterflow_pen = "butter" in text and "pen" in text
    if basic_pencil or basic_eraser or basic_sharpener or butterflow_pen:
        include_from("Default")

    deluxe_terms = ("mechanical pencil", "octane", "compass", "divider", "protractor", "set square", "geometry", "scale", "ruler", "pouch", "pencil case")
    if any(term in text for term in deluxe_terms):
        include_from("Deluxe")

    ultra_terms = ("notebook", "exercise book", "marker", "highlighter", "color pencil", "colour pencil", "refill", "paper", "sticky notes", "graph")
    if any(term in text for term in ultra_terms):
        include_from("Ultra")

    if price <= 900:
        include_from("Efficiency")

    return [plan for plan in PLAN_ORDER if plan in plans]

def default_catalog_items() -> list[dict[str, Any]]:
    source = Path("static/calculator-data.js")
    if not source.exists():
        return []
    text = source.read_text(encoding="utf-8", errors="replace")
    item_pattern = re.compile(
        r"\{\s*id:\s*\d+,\s*name:\s*'((?:\\'|[^'])*)',\s*category:\s*'((?:\\'|[^'])*)',\s*price:\s*(\d+),\s*image:\s*'((?:\\'|[^'])*)'\s*\}"
    )
    items = []
    for name, category, price, icon in item_pattern.findall(text):
        clean_name = name.replace("\\'", "'")
        clean_category = category.replace("\\'", "'")
        item_price = int(price)
        items.append({
            "name": clean_name,
            "price": item_price,
            "category": clean_category,
            "icon": icon.replace("\\'", "'"),
            "plans": plan_names_from_catalog_item(clean_name, clean_category, item_price),
        })
    return items

def seed_items() -> None:
    catalog = default_catalog_items()
    if not catalog:
        return
    timestamp = now_iso()
    with get_db() as db:
        item_count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        if item_count >= 20:
            return
        for item in catalog:
            existing = db.execute("SELECT 1 FROM items WHERE lower(name) = lower(?) LIMIT 1", (item["name"],)).fetchone()
            if existing:
                continue
            db.execute(
                "INSERT INTO items (name,price,category,icon,plans,active,created_at,updated_at) VALUES (?,?,?,?,?,1,?,?)",
                (
                    item["name"],
                    item["price"],
                    item["category"],
                    item["icon"],
                    json.dumps(item["plans"]),
                    timestamp,
                    timestamp,
                ),
            )
        db.commit()

init_db()

# ---------- Session helpers ----------
def get_session_profile_id() -> str | None:
    profile_id = session.get("profile_id")
    return profile_id if isinstance(profile_id, str) else None

def row_to_profile(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "authProvider": row["auth_provider"],
        "name": row["name"],
        "email": row["email"],
        "plan": row["plan"],
        "school": row["school"],
        "grade": row["grade"],
        "avatarInitials": row["avatar_initials"],
        "avatarColor": row["avatar_color"],
        "avatarUrl": row["avatar_url"],
        "theme": row["theme"],
        "role": row["role"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "claimsThisCycle": row["claims_this_cycle"],
        "shareToken": row["share_token"],
    }

def get_profile(profile_id: str | None = None) -> dict[str, Any] | None:
    profile_id = profile_id or get_session_profile_id()
    if not profile_id:
        return None
    with get_db() as db:
        row = db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return row_to_profile(row)

def initials_from_name(name: str) -> str:
    parts = [part[0] for part in name.split() if part]
    return ("".join(parts[:2]) or "PI").upper()[:3]

def create_guest_profile(name: str = "Guest Student", role: str = "student") -> dict[str, Any]:
    clean_name = clean_text(name, 80) or "Guest Student"
    profile_id = str(uuid.uuid4())
    timestamp = now_iso()
    with get_db() as db:
        db.execute(
            "INSERT INTO profiles (id, auth_provider, name, avatar_initials, role, created_at, updated_at) VALUES (?, 'guest', ?, ?, ?, ?, ?)",
            (profile_id, clean_name, initials_from_name(clean_name), role, timestamp, timestamp),
        )
        db.commit()
    session["profile_id"] = profile_id
    session["auth_skipped"] = True
    return get_profile(profile_id) or {}

def upsert_google_profile(google_sub: str, name: str, email: str, avatar_url: str, role: str = "student") -> dict[str, Any]:
    clean_name = clean_text(name, 80) or "Google Student"
    clean_email = clean_text(email, 120)
    timestamp = now_iso()
    with get_db() as db:
        row = db.execute("SELECT * FROM profiles WHERE google_sub = ?", (google_sub,)).fetchone()
        if row:
            profile_id = row["id"]
            db.execute(
                "UPDATE profiles SET auth_provider='google', name=?, email=?, avatar_url=?, role=?, updated_at=? WHERE id=?",
                (clean_name, clean_email, clean_text(avatar_url, 500), role, timestamp, profile_id),
            )
        else:
            profile_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO profiles (id, auth_provider, google_sub, name, email, avatar_initials, avatar_url, role, created_at, updated_at) VALUES (?, 'google', ?, ?, ?, ?, ?, ?, ?, ?)",
                (profile_id, google_sub, clean_name, clean_email, initials_from_name(clean_name), clean_text(avatar_url, 500), role, timestamp, timestamp),
            )
        db.commit()
    session["profile_id"] = profile_id
    session["auth_skipped"] = False
    return get_profile(profile_id) or {}

def sanitize_profile_update(data: dict[str, Any]) -> dict[str, str]:
    plan = clean_text(data.get("plan"), 40)
    theme = clean_text(data.get("theme"), 20) or "default"
    avatar_color = clean_text(data.get("avatarColor"), 24) or "#e8c84a"
    if plan not in VALID_PLANS:
        plan = ""
    if theme not in VALID_THEMES:
        theme = "default"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", avatar_color):
        avatar_color = "#e8c84a"
    name = clean_text(data.get("name"), 80)
    avatar_initials = clean_text(data.get("avatarInitials"), 3).upper()
    return {
        "name": name,
        "email": clean_text(data.get("email"), 120),
        "plan": plan,
        "school": clean_text(data.get("school"), 80),
        "grade": clean_text(data.get("grade"), 40),
        "avatarInitials": avatar_initials or initials_from_name(name),
        "avatarColor": avatar_color,
        "theme": theme,
    }

def normalize_plan(value: Any) -> str:
    plan = clean_text(value, 40)
    return plan if plan in PLAN_ORDER else ""

def normalize_order_status(value: Any) -> str:
    status = clean_text(value, 20).lower()
    status = ORDER_STATUS_ALIASES.get(status, status)
    return status if status in VALID_ORDER_STATUSES else ""

def safe_int(value: Any, default: int = 0, minimum: int = 0, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number

def item_is_covered(item: sqlite3.Row, plan: str) -> bool:
    if not plan:
        return False
    try:
        plans = json.loads(item["plans"])
    except Exception:
        plans = []
    return isinstance(plans, list) and plan in plans

def validate_order_items(raw_items: Any, plan: str) -> tuple[list[dict[str, Any]], int, int, str | None]:
    if not isinstance(raw_items, list) or not raw_items:
        return [], 0, 0, "Items list required"
    if len(raw_items) > 50:
        return [], 0, 0, "Too many items in one order"

    requested: dict[str, int] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            return [], 0, 0, "Invalid item payload"
        name = clean_text(raw_item.get("name"), 100)
        qty = safe_int(raw_item.get("qty", 1), default=1, minimum=1, maximum=20)
        if not name:
            return [], 0, 0, "Every item needs a name"
        requested[name] = requested.get(name, 0) + qty

    normalized_items: list[dict[str, Any]] = []
    total_price = 0
    covered_value = 0
    with get_db() as db:
        for name, qty in requested.items():
            item = db.execute("SELECT * FROM items WHERE lower(name) = lower(?) AND active = 1", (name,)).fetchone()
            if not item:
                return [], 0, 0, f"Item is unavailable: {name}"
            covered = item_is_covered(item, plan)
            line_total = int(item["price"]) * qty
            total_price += line_total
            if covered:
                covered_value += line_total
            normalized_items.append({
                "name": item["name"],
                "price": int(item["price"]),
                "qty": qty,
                "covered": covered,
                "icon": item["icon"],
            })

    return normalized_items, total_price, covered_value, None

@app.context_processor
def template_context():
    return {
        "asset_version": "20260508",
        "google_client_id": GOOGLE_CLIENT_ID,
        "google_configured": bool(GOOGLE_CLIENT_ID),
        "ai_provider": AI_PROVIDER,
        "gemini_api_key": GEMINI_API_KEY,
    }

# ─── ROUTES ──────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", **template_context())

@app.route("/profile")
def profile_page():
    return render_template("profile.html", **template_context())

@app.route("/shop")
def shop_page():
    return render_template("shopping.html", **template_context())

@app.route("/tnc")
def tnc_page():
    return render_template("tnc.html", **template_context())

@app.route("/privacy")
def privacy_page():
    # privacy.html template does not exist; render tnc.html as fallback
    # (or create a dedicated privacy.html in templates to replace this)
    return render_template("tnc.html", **template_context())

@app.route("/club")
def club_page():
    return render_template("club.html", **template_context())

@app.route("/parent/<token>")
def parent_view(token):
    return render_template("parent.html", token=token, **template_context())

@app.route("/parent")
def parent_portal():
    return render_template("parent.html", token=None, **template_context())

@app.route("/admin")
def admin_page():
    if not is_admin():
        return "Access denied", 403
    return render_template("admin.html", **template_context())

@app.route("/scanner")
def scanner_page():
    return render_template("scanner.html", **template_context())

@app.route("/plans-explorer")
def plans_explorer_page():
    return render_template("plans-explorer.html", **template_context())

@app.route("/api/scan", methods=["POST"])
@limiter.limit("20 per minute")
def api_scan():
    if not gemini_model:
        return jsonify({"error": "Gemini AI is not configured"}), 503
    data = request.get_json(silent=True) or {}
    b64_image = data.get("image")
    if not b64_image:
        return jsonify({"error": "No image provided"}), 400
    
    system_prompt = """You are a stationery detection AI for Pencil Insurance (OWIS Bangalore student service).
Analyse the image and identify school stationery items visible in it.

Plans (cumulative — higher tiers include all lower items):
- Default: pencil (HB), eraser, sharpener, butterflow pen
- Deluxe: + octane pen, compass, divider, mechanical pencil, scale/ruler, pencil pouch
- Ultra: + notebooks, exercise books, markers, highlighters, coloured pencils, refills
- Efficiency: + any stationery item up to ₹900 value, art/shading supplies, premium notebooks

Return ONLY valid JSON, no markdown fences, no extra text:
{"items":[{"name":"short capitalised name","emoji":"emoji","lowestPlanCovered":"Default|Deluxe|Ultra|Efficiency|null","confidence":"high|medium|low","notes":"optional short note"}]}
Rules: only list actually visible items; if nothing stationery-related is visible return {"items":[]}; lowestPlanCovered is the first plan tier that covers this item (null = not covered)."""

    try:
        import base64
        if "," in b64_image:
            b64_image = b64_image.split(",")[1]
        image_bytes = base64.b64decode(b64_image)
        
        parts = [
            system_prompt,
            "Identify stationery items visible in this image and return the JSON.",
            {"mime_type": "image/jpeg", "data": image_bytes}
        ]
        
        response = gemini_model.generate_content(parts)
        text = response.text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        return jsonify({"success": True, "items": parsed.get("items", [])}), 200
    except Exception as e:
        app.logger.exception("Scan failed")
        return jsonify({"error": "AI returned unexpected format — try again"}), 500

# ─── API: AUTH ──────────────────────────────────────────

@app.route("/api/auth/guest", methods=["POST"])
@limiter.limit("10 per minute")
def api_auth_guest():
    data = request.get_json(silent=True) or {}
    role = clean_text(data.get("role"), 10) or "student"
    if role not in ("student", "parent"):
        role = "student"
    profile = create_guest_profile(clean_text(data.get("name"), 80) or "Guest Student", role=role)
    return jsonify({"success": True, "profile": profile}), 200

@app.route("/api/auth/google", methods=["POST"])
@limiter.limit("15 per minute")
def api_auth_google():
    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google OAuth client ID is not configured"}), 503
    if not GOOGLE_AUTH_AVAILABLE:
        return jsonify({"error": "Google auth dependency is not installed"}), 503

    data = request.get_json(silent=True)
    credential = data.get("credential") if isinstance(data, dict) else None
    if not credential:
        return jsonify({"error": "Google credential is required"}), 400

    try:
        claims = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        app.logger.exception("Google sign-in could not be verified")
        return jsonify({"error": str(e)}), 401

    role = clean_text(data.get("role"), 10) or "student"
    if role not in ("student", "parent"):
        role = "student"

    profile = upsert_google_profile(
        google_sub=str(claims.get("sub", "")),
        name=str(claims.get("name", "")),
        email=str(claims.get("email", "")),
        avatar_url=str(claims.get("picture", "")),
        role=role,
    )
    return jsonify({"success": True, "profile": profile}), 200

@app.route("/api/auth/role", methods=["POST"])
@limiter.limit("20 per minute")
def api_set_role():
    profile = get_profile()
    if not profile:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json(silent=True) or {}
    role = clean_text(data.get("role"), 10) or "student"
    if role not in ("student", "parent"):
        role = "student"
    with get_db() as db:
        db.execute("UPDATE profiles SET role=?, updated_at=? WHERE id=?", (role, now_iso(), profile["id"]))
        db.commit()
    return jsonify({"success": True, "role": role}), 200

@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop("profile_id", None)
    session.pop("auth_skipped", None)
    return jsonify({"success": True}), 200

# ─── API: PROFILE ───────────────────────────────────────

@app.route("/api/profile", methods=["GET"])
def api_get_profile():
    profile = get_profile()
    if not profile:
        return jsonify({"authenticated": False, "profile": None}), 200
    return jsonify({"authenticated": True, "profile": profile}), 200

@app.route("/api/profile", methods=["POST"])
@limiter.limit("30 per minute")
def api_update_profile():
    profile = get_profile()
    if not profile:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid profile payload"}), 400

    payload = sanitize_profile_update(data)
    timestamp = now_iso()
    with get_db() as db:
        db.execute(
            "UPDATE profiles SET name=?, email=?, plan=?, school=?, grade=?, avatar_initials=?, avatar_color=?, theme=?, updated_at=? WHERE id=?",
            (payload["name"], payload["email"], payload["plan"], payload["school"], payload["grade"],
             payload["avatarInitials"], payload["avatarColor"], payload["theme"], timestamp, profile["id"]),
        )
        db.commit()
    return jsonify({"success": True, "profile": get_profile(profile["id"])}), 200

@app.route("/api/profile/share-token", methods=["POST"])
@limiter.limit("10 per minute")
def generate_share_token():
    profile = get_profile()
    if not profile:
        return jsonify({"error": "Not authenticated"}), 401
    token = secrets.token_urlsafe(24)
    with get_db() as db:
        while db.execute("SELECT 1 FROM profiles WHERE share_token = ?", (token,)).fetchone():
            token = secrets.token_urlsafe(24)
        db.execute("UPDATE profiles SET share_token = ?, updated_at = ? WHERE id = ?", (token, now_iso(), profile["id"]))
        db.commit()
    return jsonify({"success": True, "shareToken": token}), 200

@app.route("/api/parent/<token>", methods=["GET"])
@limiter.limit("30 per minute")
def parent_api_view(token: str):
    token = clean_text(token, 128)
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", token):
        return jsonify({"error": "Invalid or expired link"}), 404
    with get_db() as db:
        row = db.execute("SELECT * FROM profiles WHERE share_token = ?", (token,)).fetchone()
    if not row:
        return jsonify({"error": "Invalid or expired link"}), 404
    profile = row_to_profile(row)
    with get_db() as db:
        order_rows = db.execute(
            "SELECT * FROM orders WHERE email=? ORDER BY created_at DESC LIMIT 10",
            (profile["email"],)
        ).fetchall()
    orders = [dict(r) for r in order_rows]
    for o in orders:
        try:
            o["items"] = json.loads(o["items"])
        except Exception:
            pass
    parent_profile = {
        "name": profile["name"],
        "plan": profile["plan"],
        "school": profile["school"],
        "grade": profile["grade"],
        "avatarInitials": profile["avatarInitials"],
        "avatarColor": profile["avatarColor"],
        "avatarUrl": profile["avatarUrl"],
        "claimsThisCycle": profile["claimsThisCycle"],
    }
    return jsonify({"profile": parent_profile, "orders": orders}), 200

@app.route("/api/my/orders", methods=["GET"])
@limiter.limit("40 per minute")
def my_orders():
    profile = get_profile()
    if not profile or not profile.get("email"):
        return jsonify({"orders": []}), 200
    email = profile["email"].lower()
    with get_db() as db:
        rows = db.execute("SELECT * FROM orders WHERE lower(email)=? ORDER BY created_at DESC", (email,)).fetchall()
    orders = [dict(r) for r in rows]
    for o in orders:
        try:
            o["items"] = json.loads(o["items"])
        except Exception:
            pass
    return jsonify({"orders": orders}), 200

# ─── API: ORDERS ────────────────────────────────────────

@app.route("/api/orders", methods=["POST"])
@limiter.limit("10 per minute")
def create_order():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    name = clean_text(data.get("name"), 80)
    email = clean_text(data.get("email"), 120)
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"success": False, "error": "Valid name and email required"}), 400

    email = email.lower()
    grade = clean_text(data.get("grade"), 40)
    plan = normalize_plan(data.get("plan"))
    location = clean_text(data.get("location"), 120)
    notes = clean_text(data.get("notes"), 500)
    if not location:
        return jsonify({"success": False, "error": "Delivery location required"}), 400

    items, total_price, covered_value, item_error = validate_order_items(data.get("items", []), plan)
    if item_error:
        return jsonify({"success": False, "error": item_error}), 400
    order_id = str(uuid.uuid4())
    timestamp = now_iso()

    with get_db() as db:
        db.execute(
            """INSERT INTO orders (id, name, email, grade, plan, location, notes, items, total_price, covered_value, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,'pending',?)""",
            (order_id, name, email, grade, plan, location, notes, json.dumps(items), total_price, covered_value, timestamp)
        )
        db.commit()
    return jsonify({"success": True, "orderId": order_id}), 201

@app.route("/api/admin/orders", methods=["GET"])
def admin_get_orders():
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    with get_db() as db:
        rows = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    orders = [dict(r) for r in rows]
    for o in orders:
        try:
            o["items"] = json.loads(o["items"])
        except Exception:
            pass
    return jsonify({"orders": orders}), 200

@app.route("/api/admin/orders/<order_id>", methods=["PATCH"])
def admin_update_order(order_id):
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    status = normalize_order_status(data.get("status"))
    if not status:
        return jsonify({"error": "Invalid status"}), 400
    with get_db() as db:
        db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        db.commit()
    return jsonify({"success": True}), 200

# ─── ADMIN HELPERS ────────────────────────────────────────

def is_admin() -> bool:
    profile = get_profile()
    return bool(profile and profile.get("email", "").lower() == ADMIN_EMAIL.lower())

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin():
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated

# ─── ADMIN API: USERS ─────────────────────────────────────

@app.route("/api/admin/users", methods=["GET"])
@require_admin
def admin_get_users():
    with get_db() as db:
        rows = db.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
    users = [row_to_profile(r) for r in rows]
    return jsonify({"users": users}), 200

@app.route("/api/admin/users/<user_id>", methods=["PATCH"])
@require_admin
def admin_update_user(user_id: str):
    data = request.get_json(silent=True) or {}
    plan = clean_text(data.get("plan"), 40)
    if plan not in VALID_PLANS:
        plan = ""
    claims = data.get("claimsThisCycle")
    timestamp = now_iso()
    with get_db() as db:
        if claims is not None:
            try:
                claims = max(0, int(claims))
                db.execute(
                    "UPDATE profiles SET plan=?, claims_this_cycle=?, updated_at=? WHERE id=?",
                    (plan, claims, timestamp, user_id),
                )
            except (ValueError, TypeError):
                db.execute(
                    "UPDATE profiles SET plan=?, updated_at=? WHERE id=?",
                    (plan, timestamp, user_id),
                )
        else:
            db.execute(
                "UPDATE profiles SET plan=?, updated_at=? WHERE id=?",
                (plan, timestamp, user_id),
            )
        db.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/users/<user_id>", methods=["DELETE"])
@require_admin
def admin_delete_user(user_id: str):
    with get_db() as db:
        db.execute("DELETE FROM profiles WHERE id=?", (user_id,))
        db.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/reset-claims", methods=["POST"])
@require_admin
def admin_reset_claims():
    with get_db() as db:
        db.execute("UPDATE profiles SET claims_this_cycle = 0")
        db.commit()
    return jsonify({"success": True}), 200

# ─── ADMIN API: ITEMS ─────────────────────────────────────

@app.route("/api/admin/items", methods=["GET"])
@require_admin
def admin_get_items():
    with get_db() as db:
        rows = db.execute("SELECT * FROM items ORDER BY category, name").fetchall()
    items = [dict(r) for r in rows]
    for it in items:
        try:
            it["plans"] = json.loads(it["plans"])
        except Exception:
            it["plans"] = []
    return jsonify({"items": items}), 200

@app.route("/api/admin/items", methods=["POST"])
@require_admin
def admin_create_item():
    data = request.get_json(silent=True) or {}
    name = clean_text(data.get("name"), 100)
    if not name:
        return jsonify({"error": "name required"}), 400
    try:
        price = max(0, int(data.get("price", 0)))
    except (ValueError, TypeError):
        price = 0
    category = clean_text(data.get("category"), 50) or "Misc"
    icon = clean_text(data.get("icon"), 10) or "📎"
    plans_raw = data.get("plans", [])
    plans = json.dumps([p for p in plans_raw if p in VALID_PLANS]) if isinstance(plans_raw, list) else "[]"
    timestamp = now_iso()
    with get_db() as db:
        db.execute(
            "INSERT INTO items (name,price,category,icon,plans,active,created_at,updated_at) VALUES (?,?,?,?,?,1,?,?)",
            (name, price, category, icon, plans, timestamp, timestamp),
        )
        db.commit()
        row = db.execute("SELECT * FROM items WHERE name=? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
    return jsonify({"success": True, "item": dict(row)}), 201

@app.route("/api/admin/items/<int:item_id>", methods=["PATCH"])
@require_admin
def admin_update_item(item_id: int):
    data = request.get_json(silent=True) or {}
    fields = []
    values = []
    if "name" in data:
        fields.append("name=?"); values.append(clean_text(data["name"], 100))
    if "price" in data:
        try:
            fields.append("price=?"); values.append(max(0, int(data["price"])))
        except (ValueError, TypeError):
            pass
    if "category" in data:
        fields.append("category=?"); values.append(clean_text(data["category"], 50))
    if "icon" in data:
        fields.append("icon=?"); values.append(clean_text(data["icon"], 10))
    if "plans" in data and isinstance(data["plans"], list):
        fields.append("plans=?"); values.append(json.dumps([p for p in data["plans"] if p in VALID_PLANS]))
    if "active" in data:
        fields.append("active=?"); values.append(1 if data["active"] else 0)
    if not fields:
        return jsonify({"error": "nothing to update"}), 400
    fields.append("updated_at=?"); values.append(now_iso())
    values.append(item_id)
    with get_db() as db:
        db.execute(f"UPDATE items SET {','.join(fields)} WHERE id=?", values)
        db.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/items/<int:item_id>", methods=["DELETE"])
@require_admin
def admin_delete_item(item_id: int):
    with get_db() as db:
        db.execute("DELETE FROM items WHERE id=?", (item_id,))
        db.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/plans", methods=["GET"])
@require_admin
def admin_get_plans():
    with get_db() as db:
        rows = db.execute("SELECT * FROM plan_config ORDER BY price").fetchall()
    plans = [dict(r) for r in rows]
    for p in plans:
        try:
            p["features"] = json.loads(p["features"])
        except Exception:
            p["features"] = []
    return jsonify({"plans": plans}), 200

@app.route("/api/admin/plans/<plan_name>", methods=["PATCH"])
@require_admin
def admin_update_plan(plan_name: str):
    data = request.get_json(silent=True) or {}
    fields = []
    values = []
    if "price" in data:
        try:
            fields.append("price=?"); values.append(max(0, int(data["price"])))
        except (ValueError, TypeError):
            pass
    if "description" in data:
        fields.append("description=?"); values.append(clean_text(data["description"], 200))
    if "features" in data and isinstance(data["features"], list):
        fields.append("features=?"); values.append(json.dumps([clean_text(f, 100) for f in data["features"]]))
    if "active" in data:
        fields.append("active=?"); values.append(1 if data["active"] else 0)
    if not fields:
        return jsonify({"error": "nothing to update"}), 400
    fields.append("updated_at=?"); values.append(now_iso())
    values.append(plan_name)
    with get_db() as db:
        db.execute(f"UPDATE plan_config SET {','.join(fields)} WHERE name=?", values)
        db.commit()
    return jsonify({"success": True}), 200

# ─── CLUB APIs ────────────────────────────────────────────

def is_club_member(user_id: str) -> bool:
    with get_db() as db:
        row = db.execute("SELECT 1 FROM club_members WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row)

@app.route("/api/club/announcements", methods=["GET"])
def get_announcements():
    announcements = []
    with get_db() as db:
        rows = db.execute(
            "SELECT a.id, a.title, a.body, a.posted_by, a.created_at, p.name as poster_name "
            "FROM club_announcements a LEFT JOIN profiles p ON a.posted_by = p.id "
            "ORDER BY a.created_at DESC"
        ).fetchall()
        for r in rows:
            ann = dict(r)
            comments = db.execute(
                "SELECT c.id, c.body, c.created_at, u.name as commenter_name "
                "FROM club_comments c JOIN profiles u ON c.user_id = u.id "
                "WHERE c.announcement_id = ? ORDER BY c.created_at ASC", (r["id"],)
            ).fetchall()
            ann["comments"] = [dict(com) for com in comments]
            announcements.append(ann)
    can_post = is_admin()
    profile = get_profile()
    can_comment = profile and (is_admin() or is_club_member(profile["id"]))
    return jsonify({
        "announcements": announcements,
        "canPost": can_post,
        "canComment": can_comment,
    }), 200

@app.route("/api/club/announcements", methods=["POST"])
@require_admin
def create_announcement():
    data = request.get_json(silent=True) or {}
    title = clean_text(data.get("title"), 200)
    body = clean_text(data.get("body"), 2000)
    if not title or not body:
        return jsonify({"error": "Title and body are required"}), 400
    timestamp = now_iso()
    with get_db() as db:
        db.execute(
            "INSERT INTO club_announcements (title, body, posted_by, created_at) VALUES (?, ?, ?, ?)",
            (title, body, get_session_profile_id(), timestamp),
        )
        db.commit()
    return jsonify({"success": True}), 201

@app.route("/api/club/announcements/<int:ann_id>/comments", methods=["POST"])
def add_comment(ann_id):
    profile = get_profile()
    if not profile:
        return jsonify({"error": "Not authenticated"}), 401
    if not (is_admin() or is_club_member(profile["id"])):
        return jsonify({"error": "Only approved members can comment"}), 403
    data = request.get_json(silent=True) or {}
    body = clean_text(data.get("body"), 500)
    if not body:
        return jsonify({"error": "Comment body is required"}), 400
    timestamp = now_iso()
    with get_db() as db:
        db.execute(
            "INSERT INTO club_comments (announcement_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
            (ann_id, profile["id"], body, timestamp),
        )
        db.commit()
    return jsonify({"success": True}), 201

@app.route("/api/club/announcements/<int:ann_id>", methods=["DELETE"])
@require_admin
def delete_announcement(ann_id):
    with get_db() as db:
        db.execute("DELETE FROM club_comments WHERE announcement_id = ?", (ann_id,))
        db.execute("DELETE FROM club_announcements WHERE id = ?", (ann_id,))
        db.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/club/members", methods=["GET"])
@require_admin
def admin_get_club_members():
    with get_db() as db:
        rows = db.execute(
            "SELECT u.id, u.name, u.email, cm.approved_at FROM club_members cm "
            "JOIN profiles u ON cm.user_id = u.id ORDER BY cm.approved_at DESC"
        ).fetchall()
    members = [dict(r) for r in rows]
    return jsonify({"members": members}), 200

@app.route("/api/admin/club/members", methods=["POST"])
@require_admin
@limiter.limit("10 per minute")
def admin_add_club_member():
    data = request.get_json(silent=True) or {}
    user_id = clean_text(data.get("userId"), 100)
    if not user_id:
        return jsonify({"error": "User ID required"}), 400
    timestamp = now_iso()
    with get_db() as db:
        if not db.execute("SELECT 1 FROM profiles WHERE id = ?", (user_id,)).fetchone():
            return jsonify({"error": "User not found"}), 404
        db.execute(
            "INSERT OR IGNORE INTO club_members (user_id, approved_by, approved_at) VALUES (?, ?, ?)",
            (user_id, get_session_profile_id(), timestamp),
        )
        db.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/club/members/<user_id>", methods=["DELETE"])
@require_admin
def admin_remove_club_member(user_id: str):
    with get_db() as db:
        db.execute("DELETE FROM club_members WHERE user_id = ?", (user_id,))
        db.commit()
    return jsonify({"success": True}), 200

@app.route("/api/club/status", methods=["GET"])
def club_status():
    """Where the current user stands with the members club."""
    profile = get_profile()
    if not profile:
        return jsonify({"authenticated": False, "state": "guest"}), 200
    if is_admin():
        state = "admin"
    elif is_club_member(profile["id"]):
        state = "member"
    else:
        with get_db() as db:
            pending = db.execute(
                "SELECT 1 FROM club_applications WHERE user_id = ? AND status = 'pending'",
                (profile["id"],),
            ).fetchone()
        state = "pending" if pending else "none"
    return jsonify({"authenticated": True, "state": state}), 200


@app.route("/api/club/apply", methods=["POST"])
@limiter.limit("5 per minute")
def club_apply():
    """Self-service: a signed-in user applies to join the club."""
    profile = get_profile()
    if not profile:
        return jsonify({"error": "Please sign in to apply"}), 401
    if is_admin() or is_club_member(profile["id"]):
        return jsonify({"error": "You're already a member", "state": "member"}), 400
    reason = clean_text((request.get_json(silent=True) or {}).get("reason"), 500)
    timestamp = now_iso()
    with get_db() as db:
        if db.execute(
            "SELECT 1 FROM club_applications WHERE user_id = ? AND status = 'pending'",
            (profile["id"],),
        ).fetchone():
            return jsonify({"success": True, "state": "pending", "message": "Application already submitted"}), 200
        db.execute(
            "INSERT INTO club_applications (user_id, name, email, reason, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (profile["id"], profile.get("name", ""), profile.get("email", ""), reason, timestamp),
        )
        db.commit()
    return jsonify({"success": True, "state": "pending"}), 201


@app.route("/api/admin/club/applications", methods=["GET"])
@require_admin
def admin_get_applications():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, user_id, name, email, reason, status, created_at "
            "FROM club_applications WHERE status = 'pending' ORDER BY created_at ASC"
        ).fetchall()
    return jsonify({"applications": [dict(r) for r in rows]}), 200


@app.route("/api/admin/club/applications/<int:app_id>/approve", methods=["POST"])
@require_admin
def admin_approve_application(app_id):
    timestamp = now_iso()
    with get_db() as db:
        row = db.execute("SELECT user_id FROM club_applications WHERE id = ?", (app_id,)).fetchone()
        if not row:
            return jsonify({"error": "Application not found"}), 404
        db.execute(
            "INSERT OR IGNORE INTO club_members (user_id, approved_by, approved_at) VALUES (?, ?, ?)",
            (row["user_id"], get_session_profile_id(), timestamp),
        )
        db.execute("UPDATE club_applications SET status = 'approved' WHERE id = ?", (app_id,))
        db.commit()
    return jsonify({"success": True}), 200


@app.route("/api/admin/club/applications/<int:app_id>/reject", methods=["POST"])
@require_admin
def admin_reject_application(app_id):
    with get_db() as db:
        db.execute("UPDATE club_applications SET status = 'rejected' WHERE id = ?", (app_id,))
        db.commit()
    return jsonify({"success": True}), 200


@app.route("/api/items", methods=["GET"])
def public_get_items():
    with get_db() as db:
        rows = db.execute("SELECT * FROM items WHERE active=1 ORDER BY category, name").fetchall()
    items = [dict(r) for r in rows]
    for it in items:
        try:
            it["plans"] = json.loads(it["plans"])
        except Exception:
            it["plans"] = []
    return jsonify({"items": items}), 200

@app.route("/api/plans", methods=["GET"])
def public_get_plans():
    with get_db() as db:
        rows = db.execute("SELECT * FROM plan_config WHERE active=1 ORDER BY price").fetchall()
    plans = [dict(r) for r in rows]
    for p in plans:
        try:
            p["features"] = json.loads(p["features"])
        except Exception:
            p["features"] = []
    return jsonify({"plans": plans}), 200

def validate_messages(raw_messages: Any) -> tuple[list[dict[str, str]], str | None]:
    if not isinstance(raw_messages, list):
        return [], "messages must be an array"
    if not raw_messages or len(raw_messages) > MAX_MESSAGES:
        return [], f"messages must contain 1-{MAX_MESSAGES} items"
    messages: list[dict[str, str]] = []
    previous_role = None
    for raw_msg in raw_messages:
        if not isinstance(raw_msg, dict):
            return [], "each message must be an object"
        role = raw_msg.get("role")
        content = clean_text(raw_msg.get("content"), MAX_MESSAGE_LENGTH + 1)
        if role not in VALID_ROLES:
            return [], "invalid message role"
        if previous_role == role:
            return [], "messages must alternate roles"
        if not content:
            return [], "message content is required"
        if len(content) > MAX_MESSAGE_LENGTH:
            return [], f"message content must be {MAX_MESSAGE_LENGTH} characters or less"
        messages.append({"role": role, "content": content})
        previous_role = role
    if messages[-1]["role"] != "user":
        return [], "latest message must be from user"
    if messages[0]["role"] != "user":
        return [], "first message must be from user"
    return messages[-MAX_MESSAGES:], None

def plan_context(plan: str | None) -> str:
    if plan and plan in PLAN_SUMMARIES:
        return f"Selected plan context: {plan}. {PLAN_SUMMARIES[plan]}"
    return ""

def fallback_reply(message: str, plan: str | None = None) -> str:
    text = message.lower()
    if any(word in text for word in ("lost", "missing", "broken", "damaged")):
        return "If you lost or damaged an item during school hours, you're covered. Contact us via WhatsApp at 9901126174 or email to file a claim. We'll replace the item."
    if "child" in text and ("profile" in text or "view" in text):
        return "To view your child's profile, ask them to share their token from their Profile page. They can generate a 'Parent View Link' and send it to you. Then visit /parent and enter the token."
    if "how" in text and "claim" in text:
        return "To file a claim, WhatsApp us at 9901126174 or email pencil.insurance.buisness@gmail.com. Tell us what you lost, when it happened (school-time), and your plan. We'll arrange a replacement."
    if "upgrade" in text:
        return "You can upgrade your plan anytime. Contact us with your current plan and the plan you want, and we'll sort out the pro-rated difference."
    if "cancel" in text or "refund" in text:
        return "You can cancel anytime. If you haven't made any claims this cycle, you get a full refund. Just let us know."
    if "plan" in text and ("cover" in text or "includes" in text):
        return "Plans cover school-time losses of listed stationery items. Default (₹60/mo) covers pencil, sharpener, eraser, Butterflow pen. Deluxe adds geometry tools. Ultra adds notebooks and markers. Efficiency includes premium art supplies and priority support."
    return "I'm here to help with Pencil Insurance plans, claims, and school stationery. Ask me about coverage, filing a claim, or upgrading your plan."

def call_gemini(messages: list[dict[str, str]], plan: str | None) -> str:
    if not gemini_model:
        raise RuntimeError("Gemini API key is not configured or model unavailable")
    
    recent = messages[-6:] if len(messages) > 6 else messages
    
    history = [
        {"role": "user", "parts": ["System: " + SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Understood."]},
    ]
    
    for msg in recent[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        content = msg["content"][:250] if msg["content"] else ""
        history.append({"role": role, "parts": [content]})
    
    chat = gemini_model.start_chat(history=history)
    prompt = f"{plan_context(plan)}\n\nStudent message: {recent[-1]['content']}"
    response = chat.send_message(prompt, generation_config={"max_output_tokens": 800})
    reply = response.text if response.text else ""
    return clean_text(reply, 2000)

@app.route("/api/chat", methods=["POST"])
@limiter.limit("10 per minute")
def chat():
    data = request.get_json(silent=True)
    if not data or "messages" not in data:
        return jsonify({"error": "messages are required"}), 400
    messages, error = validate_messages(data.get("messages"))
    if error:
        return jsonify({"error": error}), 400
    plan = clean_text(data.get("plan"), 40)
    if plan not in PLAN_SUMMARIES:
        plan = None
    latest_message = messages[-1]["content"]
    source = "fallback"
    reply = fallback_reply(latest_message, plan)
    try:
        if gemini_model:
            reply = call_gemini(messages, plan)
            source = "ai"
    except Exception:
        app.logger.warning("Gemini call failed, using fallback", exc_info=True)
    return jsonify({"reply": reply, "source": source, "provider": AI_PROVIDER}), 200

# ─── CONTACT (with captcha) ──────────────────────────────

def validate_contact_payload(data: Any) -> tuple[dict[str, str], dict[str, str]]:
    data = data if isinstance(data, dict) else {}
    payload = {
        "name": clean_text(data.get("name"), 80),
        "email": clean_text(data.get("email"), 120),
        "plan": clean_text(data.get("plan"), 80),
        "message": clean_text(data.get("message"), 1000),
    }
    errors: dict[str, str] = {}
    if len(payload["name"]) < 2:
        errors["name"] = "Name is required."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload["email"]):
        errors["email"] = "Enter a valid email address."
    if len(payload["message"]) < 10:
        errors["message"] = "Message must be at least 10 characters."
    return payload, errors

@app.route("/api/contact", methods=["POST"])
@limiter.limit("5 per minute")
def contact():
    data = request.get_json(silent=True)
    # Optional captcha check (if frontend sends it)
    if data and "captchaAnswer" in data and "captchaHidden" in data:
        try:
            if int(data["captchaAnswer"]) != int(data["captchaHidden"]):
                return jsonify({"success": False, "errors": {"captcha": "Incorrect anti‑spam answer."}}), 400
        except (ValueError, TypeError):
            pass
    payload, errors = validate_contact_payload(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    submissions.append(payload)
    app.logger.info("New contact submission for %s", payload["email"])
    return jsonify({"success": True}), 200

@app.errorhandler(429)
def ratelimit_handler(error):
    return jsonify({"error": "Too many requests. Please wait a minute and try again."}), 429

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Something went wrong"}), 500

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("PORT", "5000")))