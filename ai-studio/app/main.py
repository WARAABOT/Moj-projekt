"""Web server: ploča, API za ploču, kanali (profili) i povezivanje YouTube/TikTok računa."""
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import channels, db, orchestrator
from .agents import crew, init_team
from .config import (DASHBOARD_PASSWORD, DASHBOARD_USER, DEMO_MODE, MEDIA_DIR, PUBLIC_BASE_URL, ROOT,
                     TIKTOK_CLIENT_KEY, TIMEZONE, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET)
from .services import branding, platforms, tiktok, tts, youtube

WEB = ROOT / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    channels.ensure_default()
    init_team()
    stop = orchestrator.start()
    yield
    stop.set()


app = FastAPI(lifespan=lifespan, title="AI Studio")
# /media je javan jer Instagram preuzima video s tvog servera; imena datoteka su nasumična
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
security = HTTPBasic(auto_error=False)


def auth(creds: HTTPBasicCredentials | None = Depends(security)):
    if not DASHBOARD_PASSWORD:
        if DEMO_MODE:  # demo samo simulira, pa smije bez lozinke (za probu na svom računalu)
            return
        raise HTTPException(503, "Postavi DASHBOARD_PASSWORD u .env da bi ploča radila")
    ok = creds and secrets.compare_digest(creds.username, DASHBOARD_USER) and \
        secrets.compare_digest(creds.password, DASHBOARD_PASSWORD)
    if not ok:
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})


app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/", dependencies=[Depends(auth)])
def index():
    return FileResponse(WEB / "index.html")


def _media_url(path: str | None) -> str | None:
    return f"/media/{path}" if path else None


def _day_start() -> float:
    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def _filter(cid: int | None, col: str = "channel_id") -> tuple[str, tuple]:
    """SQL uvjet za odabrani kanal (ili sve kanale)."""
    return (f" AND {col}=?", (cid,)) if cid else ("", ())


def _connections(ch: dict) -> dict:
    return {p: platforms.get(p).ready(ch) for p in platforms.enabled(ch)}


@app.get("/api/state", dependencies=[Depends(auth)])
def state(channel: int | None = None):
    today = _day_start()
    chs = channels.all()
    names = {c["id"]: c["name"] for c in chs}
    wv, av = _filter(channel, "v.channel_id")
    w, a = _filter(channel)

    posts = db.rows(f"""SELECT p.*, v.channel_id FROM posts p JOIN videos v ON v.id=p.video_id
                        WHERE p.status='live'{wv}""", *av)
    latest_stats = db.rows(f"""SELECT s.* FROM stats s JOIN (SELECT channel_id, platform, MAX(ts) ts FROM stats
                               GROUP BY channel_id, platform) m
                               ON m.platform=s.platform AND m.ts=s.ts AND m.channel_id=s.channel_id
                               WHERE 1=1{_filter(channel, 's.channel_id')[0]}""", *a)
    day_ago = db.rows(f"""SELECT channel_id, platform, MIN(views) views, MIN(followers) followers FROM stats
                          WHERE ts>?{w} GROUP BY channel_id, platform""", time.time() - 86400, *a)

    views_total = sum(p["views"] for p in posts)
    followers = sum(s["followers"] for s in latest_stats)
    kpi = {
        "views_total": views_total,
        "views_24h": views_total - sum(r["views"] for r in day_ago) if day_ago else 0,
        "followers": followers,
        "followers_24h": followers - sum(r["followers"] for r in day_ago) if day_ago else 0,
        "likes": sum(p["likes"] for p in posts),
        "posts_today": sum(1 for p in posts if (p["published_at"] or 0) >= today),
        "posts_total": len(posts),
        "in_production": db.row(f"""SELECT COUNT(*) n FROM videos WHERE status IN
                                    ('approved','writing','scripted','producing','review'){w}""", *a)["n"],
    }

    shown = [c for c in chs if not channel or c["id"] == channel]
    pipeline = []
    for name in platforms.NAMES:
        using = [c for c in shown if name in platforms.enabled(c)]
        if not using:
            continue
        mine = [p for p in posts if p["platform"] == name]
        pipeline.append({
            "id": name, "name": platforms.NAMES[name],
            "ready": all(platforms.get(name).ready(c) for c in using),
            "posts": len(mine), "today": sum(1 for p in mine if (p["published_at"] or 0) >= today),
            "views": sum(p["views"] for p in mine),
            "followers": sum(s["followers"] for s in latest_stats if s["platform"] == name),
        })

    approvals = []
    for ap in db.rows(f"SELECT * FROM approvals WHERE status='pending'{w} ORDER BY created_at", *a):
        if ap["kind"] == "publish":
            v = db.row("SELECT video_path, thumb_path FROM videos WHERE id=?", ap["ref_id"]) or {}
            ap["video"], ap["thumb"] = _media_url(v.get("video_path")), _media_url(v.get("thumb_path"))
        approvals.append(ap)

    week = db.rows(f"""SELECT id, channel_id, title, status, format, scheduled_at FROM videos
                       WHERE scheduled_at BETWEEN ? AND ?{w} ORDER BY scheduled_at""",
                   today - 86400, today + 8 * 86400, *a)

    latest = db.row(f"SELECT * FROM videos WHERE status='published'{w} ORDER BY updated_at DESC LIMIT 1", *a)
    if latest:
        lp = [p for p in posts if p["video_id"] == latest["id"]]
        latest = {"id": latest["id"], "channel_id": latest["channel_id"], "title": latest["title"],
                  "format": latest["format"], "video": _media_url(latest["video_path"]),
                  "thumb": _media_url(latest["thumb_path"]), "published_at": latest["updated_at"],
                  "views": sum(p["views"] for p in lp), "likes": sum(p["likes"] for p in lp),
                  "comments": sum(p["comments"] for p in lp),
                  "links": [{"platform": p["platform"], "url": p["url"]} for p in lp if p["url"]]}

    # ukupni pregledi kroz vrijeme (jedna točka po prolazu Analysta)
    series = db.rows(f"""SELECT CAST(ts/10 AS INT)*10 t, SUM(views) views, SUM(followers) followers
                         FROM stats WHERE 1=1{w} GROUP BY t ORDER BY t DESC LIMIT 60""", *a)[::-1]

    return {
        "demo": DEMO_MODE, "timezone": TIMEZONE, "now": time.time(), "selected": channel,
        "channels": [{**channels.public(c), "connections": _connections(c)} for c in chs],
        "channel_names": names,
        "kpi": kpi, "pipeline": pipeline, "approvals": approvals, "week": week, "latest": latest,
        "series": series,
        "agents": db.rows("SELECT * FROM agents"),
        "videos": db.rows(f"""SELECT id, channel_id, topic, title, status, format, error, scheduled_at, updated_at
                              FROM videos WHERE 1=1{w} ORDER BY id DESC LIMIT 25""", *a),
        "comments": db.rows(f"""SELECT c.*, p.platform, v.channel_id FROM comments c JOIN posts p ON p.id=c.post_id
                                JOIN videos v ON v.id=p.video_id WHERE 1=1{wv} ORDER BY c.ts DESC LIMIT 15""", *av),
        "events": db.rows(f"SELECT * FROM events WHERE 1=1{w} ORDER BY id DESC LIMIT 40", *a),
        "connect": {
            "youtube": bool(YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET and PUBLIC_BASE_URL),
            "tiktok": bool(TIKTOK_CLIENT_KEY and PUBLIC_BASE_URL),
        },
        "voices": tts.VOICES,
    }


class Decision(BaseModel):
    approve: bool
    text: str | None = None


@app.post("/api/approvals/{aid}", dependencies=[Depends(auth)])
def decide(aid: int, d: Decision):
    try:
        crew.decide(aid, d.approve, d.text)
    except Exception as e:
        raise HTTPException(502, str(e))
    return {"ok": True}


@app.post("/api/videos/{vid}/retry", dependencies=[Depends(auth)])
def retry(vid: int):
    crew.retry(vid)
    return {"ok": True}


# ---------- kanali ----------

class ChannelIn(BaseModel):
    name: str | None = None
    niche: str | None = None
    language: str | None = None
    color: str | None = None
    voice: str | None = None
    post_times: str | None = None
    long_enabled: bool | None = None
    long_days: str | None = None
    long_time: str | None = None
    platforms: str | None = None
    auto_topics: bool | None = None
    auto_publish: bool | None = None
    ig_user_id: str | None = None
    ig_token: str | None = None
    active: bool | None = None


def _check(data: dict):
    if "color" in data and not re.fullmatch(r"#[0-9a-fA-F]{6}", data["color"]):
        raise HTTPException(400, "Boja mora biti u obliku #ff2bd6")
    for t in [*(data.get("post_times") or "").split(","), data.get("long_time") or ""]:
        t = t.strip()
        if t:
            try:
                datetime.strptime(t, "%H:%M")
            except ValueError:
                raise HTTPException(400, f"Neispravno vrijeme: {t} (treba npr. 09:00)")


@app.post("/api/channels", dependencies=[Depends(auth)])
def channel_create(c: ChannelIn):
    data = c.model_dump(exclude_none=True)
    _check(data)
    return {"id": channels.create(data)}


@app.put("/api/channels/{cid}", dependencies=[Depends(auth)])
def channel_update(cid: int, c: ChannelIn):
    if not channels.get(cid):
        raise HTTPException(404, "Nema tog kanala")
    data = c.model_dump(exclude_none=True)
    _check(data)
    channels.update(cid, data)
    return {"ok": True}


class BrandingIn(BaseModel):
    tagline: str = ""


@app.post("/api/channels/{cid}/branding", dependencies=[Depends(auth)])
def channel_branding(cid: int, b: BrandingIn):
    ch = channels.get(cid)
    if not ch:
        raise HTTPException(404, "Nema tog kanala")
    color = (ch["color"] or "#ff2bd6").lstrip("#")
    accent = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    out = MEDIA_DIR / f"branding-c{cid}-{uuid.uuid4().hex[:8]}"
    files = branding.build(out, ch["name"], b.tagline or ch["niche"] or "", accent)
    return {"files": [{"label": k, "url": _media_url(p.relative_to(MEDIA_DIR).as_posix())} for k, p in files.items()]}


# ---------- povezivanje računa (OAuth), za odabrani kanal ----------

def _state_token(name: str, cid: int) -> str:
    tok = secrets.token_urlsafe(16)
    db.kv_set(f"oauth_state_{name}_{tok}", str(cid))
    return tok


def _channel_from_state(name: str, got: str) -> int:
    cid = db.kv_get(f"oauth_state_{name}_{got}") if got else ""
    if not cid:
        raise HTTPException(400, "Neispravan state, pokušaj ponovno")
    db.run("DELETE FROM kv WHERE key=?", f"oauth_state_{name}_{got}")
    return int(cid)


def _need_channel(cid: int):
    if not channels.get(cid):
        raise HTTPException(404, "Nema tog kanala")


@app.get("/auth/youtube/start", dependencies=[Depends(auth)])
def youtube_start(channel: int):
    _need_channel(channel)
    q = {"client_id": YOUTUBE_CLIENT_ID, "redirect_uri": f"{PUBLIC_BASE_URL}/auth/youtube/callback",
         "response_type": "code", "scope": " ".join(youtube.SCOPES), "access_type": "offline",
         # select_account: da možeš odabrati Google račun baš tog kanala
         "prompt": "consent select_account", "state": _state_token("youtube", channel)}
    return RedirectResponse(f"{youtube.AUTH_URL}?{urlencode(q)}")


@app.get("/auth/youtube/callback", dependencies=[Depends(auth)])
def youtube_callback(code: str, state: str):
    cid = _channel_from_state("youtube", state)
    r = httpx.post(youtube.TOKEN_URL, data={
        "code": code, "client_id": YOUTUBE_CLIENT_ID, "client_secret": YOUTUBE_CLIENT_SECRET,
        "redirect_uri": f"{PUBLIC_BASE_URL}/auth/youtube/callback", "grant_type": "authorization_code"}, timeout=30)
    r.raise_for_status()
    youtube.save_refresh_token(cid, r.json()["refresh_token"])
    return RedirectResponse(f"/?channel={cid}&connected=youtube")


@app.get("/auth/tiktok/start", dependencies=[Depends(auth)])
def tiktok_start(channel: int):
    _need_channel(channel)
    q = {"client_key": TIKTOK_CLIENT_KEY, "redirect_uri": f"{PUBLIC_BASE_URL}/auth/tiktok/callback",
         "response_type": "code", "scope": tiktok.SCOPES, "state": _state_token("tiktok", channel),
         "disable_auto_auth": 1}  # uvijek pitaj, da se možeš prijaviti drugim TikTok računom
    return RedirectResponse(f"{tiktok.AUTH_URL}?{urlencode(q)}")


@app.get("/auth/tiktok/callback", dependencies=[Depends(auth)])
def tiktok_callback(code: str, state: str):
    cid = _channel_from_state("tiktok", state)
    tiktok.exchange_code(cid, code, f"{PUBLIC_BASE_URL}/auth/tiktok/callback")
    return RedirectResponse(f"/?channel={cid}&connected=tiktok")
