"""Kanali (profili). Svaki ima svoju temu, termine, glas i račune na platformama."""
import time

from . import db
from .config import (AUTO_APPROVE_PUBLISH, AUTO_APPROVE_TOPICS, INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID, LANGUAGE,
                     LONG_DAYS, LONG_ENABLED, LONG_TIME, NICHE, PLATFORMS, POST_TIMES, env)

EDITABLE = ("name", "niche", "language", "color", "voice", "post_times", "long_enabled", "long_days", "long_time",
            "platforms", "auto_topics", "auto_publish", "ig_user_id", "ig_token", "active")
SECRET = ("ig_token",)  # ne šalje se u preglednik


def all(active_only: bool = False) -> list[dict]:
    return db.rows("SELECT * FROM channels" + (" WHERE active=1" if active_only else "") + " ORDER BY id")


def get(cid: int) -> dict | None:
    return db.row("SELECT * FROM channels WHERE id=?", cid)


def public(ch: dict) -> dict:
    out = {k: v for k, v in ch.items() if k not in SECRET}
    out["has_ig_token"] = bool(ch.get("ig_token"))
    return out


def _clean(data: dict) -> dict:
    out = {k: v for k, v in data.items() if k in EDITABLE}
    for k in ("long_enabled", "auto_topics", "auto_publish", "active"):
        if k in out:
            out[k] = 1 if out[k] in (True, 1, "1", "true", "on") else 0
    if "ig_token" in out and not out["ig_token"]:
        del out["ig_token"]  # prazno polje = ne mijenjaj spremljeni token
    return out


def create(data: dict) -> int:
    data = _clean(data)
    data.setdefault("name", "Novi kanal")
    return db.insert("channels", created_at=time.time(), **data)


def update(cid: int, data: dict):
    data = _clean(data)
    if data:
        db.update("channels", cid, **data)


# ---------- pomoćne ----------

def post_times(ch: dict) -> list[str]:
    return sorted(t.strip() for t in (ch["post_times"] or "").split(",") if t.strip())


def long_days(ch: dict) -> list[str]:
    return [d.strip().lower()[:3] for d in (ch["long_days"] or "").split(",") if d.strip()]


def platform_list(ch: dict) -> list[str]:
    return [p.strip() for p in (ch["platforms"] or "").split(",") if p.strip()]


def ensure_default():
    """Prvo pokretanje (ili nadogradnja s jednog kanala): napravi kanal iz postavki u .env."""
    if db.row("SELECT id FROM channels LIMIT 1"):
        return
    cid = create({
        "name": env("CHANNEL_NAME", "Byte Crew"), "niche": NICHE, "language": LANGUAGE,
        "voice": env("KOKORO_VOICE", "am_michael"), "post_times": ",".join(POST_TIMES),
        "long_enabled": LONG_ENABLED, "long_days": ",".join(LONG_DAYS), "long_time": LONG_TIME,
        "platforms": ",".join(PLATFORMS), "auto_topics": AUTO_APPROVE_TOPICS, "auto_publish": AUTO_APPROVE_PUBLISH,
        "ig_user_id": INSTAGRAM_USER_ID, "ig_token": INSTAGRAM_ACCESS_TOKEN,
    })
    for table in ("videos", "approvals", "stats", "events"):
        db.run(f"UPDATE {table} SET channel_id=? WHERE channel_id IS NULL", cid)
    # stari tokeni (jedan kanal) prelaze na prvi kanal
    for key in ("youtube_refresh_token", "tiktok_access_token", "tiktok_refresh_token", "tiktok_expires_at"):
        if old := db.kv_get(key):
            db.kv_set(f"{key}_{cid}", old)
    if yt := env("YOUTUBE_REFRESH_TOKEN"):
        db.kv_set(f"youtube_refresh_token_{cid}", yt)
