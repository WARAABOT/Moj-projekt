"""SQLite baza. Svaki poziv otvara svoju vezu, pa je sigurno iz više dretvi."""
import json
import sqlite3
import time
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY,
  topic TEXT, angle TEXT,
  status TEXT,              -- idea, writing, scripted, producing, review, scheduled, publishing, published, rejected, failed
  script TEXT,              -- JSON od Writera
  title TEXT, description TEXT, hashtags TEXT,
  video_path TEXT, thumb_path TEXT,
  scheduled_at REAL, error TEXT,
  created_at REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  video_id INTEGER, platform TEXT,
  status TEXT,              -- uploading, live, failed
  external_id TEXT, url TEXT,
  views INTEGER DEFAULT 0, likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
  published_at REAL, error TEXT
);
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY,
  kind TEXT,                -- topic, publish, reply
  ref_id INTEGER, title TEXT, detail TEXT,
  status TEXT DEFAULT 'pending',
  created_at REAL
);
CREATE TABLE IF NOT EXISTS agents (
  name TEXT PRIMARY KEY, role TEXT,
  state TEXT, task TEXT, progress REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, ts REAL, agent TEXT, message TEXT
);
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY,
  platform TEXT, post_id INTEGER, external_id TEXT UNIQUE,
  author TEXT, text TEXT, reply TEXT,
  status TEXT,              -- new, suggested, replied, ignored
  ts REAL
);
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY, value TEXT
);
CREATE TABLE IF NOT EXISTS stats (
  ts REAL, platform TEXT, views INTEGER, followers INTEGER
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(SCHEMA)


def rows(sql: str, *args) -> list[dict]:
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def row(sql: str, *args) -> dict | None:
    r = rows(sql, *args)
    return r[0] if r else None


def run(sql: str, *args) -> int:
    with conn() as c:
        return c.execute(sql, args).lastrowid


def insert(table: str, **data) -> int:
    cols = ",".join(data)
    marks = ",".join("?" * len(data))
    return run(f"INSERT INTO {table} ({cols}) VALUES ({marks})", *data.values())


def update(table: str, id_: int, **data):
    sets = ",".join(f"{k}=?" for k in data)
    run(f"UPDATE {table} SET {sets} WHERE id=?", *data.values(), id_)


def update_video(vid: int, **data):
    update("videos", vid, updated_at=time.time(), **data)


def video_script(v: dict) -> dict:
    return json.loads(v["script"]) if v.get("script") else {}


def kv_get(key: str, default: str = "") -> str:
    r = row("SELECT value FROM kv WHERE key=?", key)
    return r["value"] if r else default


def kv_set(key: str, value: str):
    run("INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", key, value)
