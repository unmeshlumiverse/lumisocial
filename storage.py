"""
Run-history, Users, and Targets storage (SQLite — built in, zero extra dependencies, $0).

Each monitoring run saves an aggregate snapshot so you can chart how sentiment,
emotion, and volume move over time. Used by both the dashboard (auto-save each
run) and scheduled_run.py (cron-friendly headless runs).
"""

import os
import json
import sqlite3
import hashlib
import datetime as dt
import pandas as pd

DB_PATH = os.environ.get("MONITOR_DB", "monitor_history.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    with _conn() as c:
        # History runs
        c.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT, ts TEXT, sources TEXT,
                total INTEGER, positive INTEGER, negative INTEGER, neutral INTEGER,
                positivity_ratio REAL, avg_score REAL,
                dominant_emotion TEXT, emotion_json TEXT, themes_json TEXT
            )"""
        )
        
        # User management table
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'ANALYST',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        
        # Tracked targets/entities table
        c.execute(
            """CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                keywords TEXT,
                excluded_keywords TEXT,
                location_hint TEXT,
                org_hint TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        
        # Seed default super admin user if no users exist
        cur = c.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
                ("admin@lumisocial.com", _hash_pw("admin123"), "SUPER_ADMIN")
            )


def save_run(term, stats, sources, dominant_emotion, emotion_counts, themes):
    """Persist one run's aggregate snapshot. Best-effort; never raises."""
    try:
        init_db()
        with _conn() as c:
            c.execute(
                """INSERT INTO runs
                   (term, ts, sources, total, positive, negative, neutral,
                    positivity_ratio, avg_score, dominant_emotion, emotion_json, themes_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    term,
                    dt.datetime.now().isoformat(timespec="seconds"),
                    ",".join(sources),
                    int(stats["total"]),
                    int(stats["positive"]),
                    int(stats["negative"]),
                    int(stats["neutral"]),
                    (float(stats["positivity_ratio"]) if stats["positivity_ratio"] is not None else None),
                    (float(stats["avg_score"]) if stats["avg_score"] is not None else None),
                    dominant_emotion,
                    json.dumps(emotion_counts),
                    json.dumps(themes)[:20000],
                ),
            )
        return True
    except Exception:
        return False


def load_history(term=None, limit=500) -> pd.DataFrame:
    """Return run history (oldest→newest for a term, or most-recent overall)."""
    try:
        init_db()
        with _conn() as c:
            if term:
                cur = c.execute("SELECT * FROM runs WHERE term=? ORDER BY ts ASC", (term,))
            else:
                cur = c.execute("SELECT * FROM runs ORDER BY ts DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)
        if not df.empty:
            df["ts"] = pd.to_datetime(df["ts"])
        return df
    except Exception:
        return pd.DataFrame()


def list_terms():
    try:
        init_db()
        with _conn() as c:
            return [r[0] for r in c.execute(
                "SELECT DISTINCT term FROM runs ORDER BY term").fetchall()]
    except Exception:
        return []


# ==================== User Management Helpers ====================

def create_user(email: str, password: str, role: str = "ANALYST") -> bool:
    try:
        init_db()
        with _conn() as c:
            c.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
                (email.strip().lower(), _hash_pw(password), role)
            )
        return True
    except Exception:
        return False


def verify_user(email: str, password: str):
    try:
        init_db()
        with _conn() as c:
            cur = c.execute(
                "SELECT id, email, role FROM users WHERE email=? AND password_hash=?",
                (email.strip().lower(), _hash_pw(password))
            )
            row = cur.fetchone()
            if row:
                return {"id": row[0], "email": row[1], "role": row[2]}
    except Exception:
        pass
    return None


def list_users():
    try:
        init_db()
        with _conn() as c:
            cur = c.execute("SELECT id, email, role, created_at FROM users ORDER BY id ASC")
            rows = cur.fetchall()
            return [{"id": r[0], "email": r[1], "role": r[2], "created_at": r[3]} for r in rows]
    except Exception:
        return []


def delete_user(user_id: int) -> bool:
    try:
        init_db()
        with _conn() as c:
            c.execute("DELETE FROM users WHERE id=?", (user_id,))
        return True
    except Exception:
        return False


# ==================== Target / Entity Management Helpers ====================

def save_target(name: str, category: str, keywords: str, excluded_keywords: str, location_hint: str, org_hint: str) -> bool:
    try:
        init_db()
        with _conn() as c:
            c.execute(
                """INSERT INTO targets (name, category, keywords, excluded_keywords, location_hint, org_hint)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name.strip(), category.strip(), keywords.strip(), excluded_keywords.strip(), location_hint.strip(), org_hint.strip())
            )
        return True
    except Exception:
        return False


def update_target(target_id: int, name: str, category: str, keywords: str, excluded_keywords: str, location_hint: str, org_hint: str) -> bool:
    try:
        init_db()
        with _conn() as c:
            c.execute(
                """UPDATE targets SET name=?, category=?, keywords=?, excluded_keywords=?, location_hint=?, org_hint=?
                   WHERE id=?""",
                (name.strip(), category.strip(), keywords.strip(), excluded_keywords.strip(), location_hint.strip(), org_hint.strip(), target_id)
            )
        return True
    except Exception:
        return False


def list_targets():
    try:
        init_db()
        with _conn() as c:
            cur = c.execute("SELECT id, name, category, keywords, excluded_keywords, location_hint, org_hint FROM targets ORDER BY id DESC")
            rows = cur.fetchall()
            return [{
                "id": r[0], "name": r[1], "category": r[2], "keywords": r[3],
                "excluded_keywords": r[4], "location_hint": r[5], "org_hint": r[6]
            } for r in rows]
    except Exception:
        return []


def delete_target(target_id: int) -> bool:
    try:
        init_db()
        with _conn() as c:
            c.execute("DELETE FROM targets WHERE id=?", (target_id,))
        return True
    except Exception:
        return False
