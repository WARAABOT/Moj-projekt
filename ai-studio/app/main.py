"""Web server: ploča, API za ploču i povezivanje YouTube/TikTok računa."""
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, orchestrator
from .agents import crew, init_team
from .config import (DASHBOARD_PASSWORD, DASHBOARD_USER, DEMO_MODE, MEDIA_DIR, NICHE, PUBLIC_BASE_URL, ROOT,
                     TIKTOK_CLIENT_KEY, TIMEZONE, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET)
from .services import platforms, tiktok, youtube

WEB = ROOT / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
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


@app.get("/api/state", dependencies=[Depends(auth)])
def state():
    today = _day_start()
    posts = db.rows("SELECT * FROM posts WHERE status='live'")
    latest_stats = db.rows("""SELECT s.* FROM stats s JOIN (SELECT platform, MAX(ts) ts FROM stats GROUP BY platform) m
                              ON m.platform=s.platform AND m.ts=s.ts""")
    day_ago = {r["platform"]: r for r in db.rows(
        "SELECT platform, MIN(views) views, MIN(followers) followers FROM stats WHERE ts>? GROUP BY platform",
        time.time() - 86400)}

    views_total = sum(p["views"] for p in posts)
    followers = sum(s["followers"] for s in latest_stats)
    kpi = {
        "views_total": views_total,
        "views_24h": views_total - sum(r["views"] for r in day_ago.values()) if day_ago else 0,
        "followers": followers,
        "followers_24h": followers - sum(r["followers"] for r in day_ago.values()) if day_ago else 0,
        "likes": sum(p["likes"] for p in posts),
        "posts_today": sum(1 for p in posts if (p["published_at"] or 0) >= today),
        "posts_total": len(posts),
        "in_production": db.row("SELECT COUNT(*) n FROM videos WHERE status IN "
                                "('approved','writing','scripted','producing','review')")["n"],
    }

    pipeline = []
    for name in platforms.enabled():
        mine = [p for p in posts if p["platform"] == name]
        st = next((s for s in latest_stats if s["platform"] == name), None)
        pipeline.append({
            "id": name, "name": platforms.NAMES[name], "ready": platforms.get(name).ready(),
            "posts": len(mine), "today": sum(1 for p in mine if (p["published_at"] or 0) >= today),
            "views": sum(p["views"] for p in mine), "followers": st["followers"] if st else 0,
        })

    approvals = []
    for a in db.rows("SELECT * FROM approvals WHERE status='pending' ORDER BY created_at"):
        if a["kind"] == "publish":
            v = db.row("SELECT video_path, thumb_path FROM videos WHERE id=?", a["ref_id"]) or {}
            a["video"], a["thumb"] = _media_url(v.get("video_path")), _media_url(v.get("thumb_path"))
        approvals.append(a)

    week = db.rows("""SELECT id, title, status, scheduled_at FROM videos
                      WHERE scheduled_at BETWEEN ? AND ? ORDER BY scheduled_at""", today - 86400, today + 8 * 86400)

    latest = db.row("SELECT * FROM videos WHERE status='published' ORDER BY updated_at DESC LIMIT 1")
    if latest:
        lp = [p for p in posts if p["video_id"] == latest["id"]]
        latest = {"id": latest["id"], "title": latest["title"], "video": _media_url(latest["video_path"]),
                  "thumb": _media_url(latest["thumb_path"]), "published_at": latest["updated_at"],
                  "views": sum(p["views"] for p in lp), "likes": sum(p["likes"] for p in lp),
                  "comments": sum(p["comments"] for p in lp),
                  "links": [{"platform": p["platform"], "url": p["url"]} for p in lp if p["url"]]}

    # ukupni pregledi kroz vrijeme (jedna točka po prolazu Analysta)
    series = db.rows("""SELECT CAST(ts/10 AS INT)*10 t, SUM(views) views, SUM(followers) followers
                        FROM stats GROUP BY t ORDER BY t DESC LIMIT 60""")[::-1]

    return {
        "demo": DEMO_MODE, "niche": NICHE, "timezone": TIMEZONE, "now": time.time(),
        "kpi": kpi, "pipeline": pipeline, "approvals": approvals, "week": week, "latest": latest,
        "series": series,
        "agents": db.rows("SELECT * FROM agents"),
        "videos": db.rows("""SELECT id, topic, title, status, error, scheduled_at, thumb_path, updated_at
                             FROM videos ORDER BY id DESC LIMIT 25"""),
        "comments": db.rows("""SELECT c.*, p.platform FROM comments c JOIN posts p ON p.id=c.post_id
                               ORDER BY c.ts DESC LIMIT 15"""),
        "events": db.rows("SELECT * FROM events ORDER BY id DESC LIMIT 40"),
        "connect": {
            "youtube": bool(YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET and PUBLIC_BASE_URL),
            "tiktok": bool(TIKTOK_CLIENT_KEY and PUBLIC_BASE_URL),
        },
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


# ---------- povezivanje računa (OAuth) ----------

def _state_token(name: str) -> str:
    tok = secrets.token_urlsafe(16)
    db.kv_set(f"oauth_state_{name}", tok)
    return tok


def _check_state(name: str, got: str):
    if not got or not secrets.compare_digest(got, db.kv_get(f"oauth_state_{name}")):
        raise HTTPException(400, "Neispravan state, pokušaj ponovno")


@app.get("/auth/youtube/start", dependencies=[Depends(auth)])
def youtube_start():
    q = {"client_id": YOUTUBE_CLIENT_ID, "redirect_uri": f"{PUBLIC_BASE_URL}/auth/youtube/callback",
         "response_type": "code", "scope": " ".join(youtube.SCOPES), "access_type": "offline",
         "prompt": "consent", "state": _state_token("youtube")}
    return RedirectResponse(f"{youtube.AUTH_URL}?{urlencode(q)}")


@app.get("/auth/youtube/callback", dependencies=[Depends(auth)])
def youtube_callback(code: str, state: str):
    _check_state("youtube", state)
    r = httpx.post(youtube.TOKEN_URL, data={
        "code": code, "client_id": YOUTUBE_CLIENT_ID, "client_secret": YOUTUBE_CLIENT_SECRET,
        "redirect_uri": f"{PUBLIC_BASE_URL}/auth/youtube/callback", "grant_type": "authorization_code"}, timeout=30)
    r.raise_for_status()
    db.kv_set("youtube_refresh_token", r.json()["refresh_token"])
    return RedirectResponse("/?connected=youtube")


@app.get("/auth/tiktok/start", dependencies=[Depends(auth)])
def tiktok_start():
    q = {"client_key": TIKTOK_CLIENT_KEY, "redirect_uri": f"{PUBLIC_BASE_URL}/auth/tiktok/callback",
         "response_type": "code", "scope": tiktok.SCOPES, "state": _state_token("tiktok")}
    return RedirectResponse(f"{tiktok.AUTH_URL}?{urlencode(q)}")


@app.get("/auth/tiktok/callback", dependencies=[Depends(auth)])
def tiktok_callback(code: str, state: str):
    _check_state("tiktok", state)
    tiktok.exchange_code(code, f"{PUBLIC_BASE_URL}/auth/tiktok/callback")
    return RedirectResponse("/?connected=tiktok")
