"""
Run-history storage (SQLite — built in, zero extra dependencies, $0).

Each monitoring run saves an aggregate snapshot so you can chart how sentiment,
emotion, and volume move over time. Used by both the dashboard (auto-save each
run) and scheduled_run.py (cron-friendly headless runs).
"""

import os
import json
import sqlite3
import datetime as dt

import pandas as pd

DB_PATH = os.environ.get("MONITOR_DB", "monitor_history.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT, ts TEXT, sources TEXT,
                total INTEGER, positive INTEGER, negative INTEGER, neutral INTEGER,
                positivity_ratio REAL, avg_score REAL,
                dominant_emotion TEXT, emotion_json TEXT, themes_json TEXT
            )"""
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
