"""TikTok Content Posting API.

TIKTOK_MODE=inbox  -> video stiže u TikTok aplikaciju kao skica, a ti ga objaviš (radi i bez odobrenja aplikacije)
TIKTOK_MODE=direct -> odmah javno (TikTok mora odobriti tvoju aplikaciju za Direct Post)
"""
import time
from pathlib import Path

import httpx

from .. import db
from ..config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_MODE, TIKTOK_PRIVACY

API = "https://open.tiktokapis.com/v2"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
SCOPES = "user.info.basic,user.info.stats,video.upload,video.publish,video.list"


def ready() -> bool:
    return bool(TIKTOK_CLIENT_KEY and db.kv_get("tiktok_refresh_token"))


def save_tokens(data: dict):
    db.kv_set("tiktok_access_token", data["access_token"])
    db.kv_set("tiktok_refresh_token", data["refresh_token"])
    db.kv_set("tiktok_expires_at", str(time.time() + int(data.get("expires_in", 86400)) - 300))


def exchange_code(code: str, redirect_uri: str):
    r = httpx.post(f"{API}/oauth/token/", data={
        "client_key": TIKTOK_CLIENT_KEY, "client_secret": TIKTOK_CLIENT_SECRET, "code": code,
        "grant_type": "authorization_code", "redirect_uri": redirect_uri}, timeout=30)
    r.raise_for_status()
    save_tokens(r.json())


def _token() -> str:
    # pristupni token traje 24 h, pa ga obnavljamo refresh tokenom
    if time.time() > float(db.kv_get("tiktok_expires_at", "0")):
        r = httpx.post(f"{API}/oauth/token/", data={
            "client_key": TIKTOK_CLIENT_KEY, "client_secret": TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token", "refresh_token": db.kv_get("tiktok_refresh_token")}, timeout=30)
        r.raise_for_status()
        save_tokens(r.json())
    return db.kv_get("tiktok_access_token")


def _post(path: str, body: dict, **params) -> dict:
    r = httpx.post(f"{API}{path}", params=params, json=body, timeout=60,
                   headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json; charset=UTF-8"})
    data = r.json()
    if r.status_code >= 400 or data.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok {path}: {data.get('error')}")
    return data.get("data", {})


def upload(video: Path, title: str, description: str, tags: list[str], thumb: Path) -> tuple[str, str]:
    size = video.stat().st_size
    chunk = size if size <= 64 * 2**20 else 10 * 2**20
    count = max(1, size // chunk)  # zadnji komad preuzima ostatak, kako TikTok traži
    source = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}
    caption = f"{title} {' '.join('#' + t for t in tags)}"[:2200]
    if TIKTOK_MODE == "direct":
        data = _post("/post/publish/video/init/", {
            "post_info": {"title": caption, "privacy_level": TIKTOK_PRIVACY, "is_aigc": True,
                          "disable_comment": False, "video_cover_timestamp_ms": 1000},
            "source_info": source})
    else:
        data = _post("/post/publish/inbox/video/init/", {"source_info": source})

    with video.open("rb") as fh:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1
            fh.seek(start)
            body = fh.read(end - start + 1)
            r = httpx.put(data["upload_url"], content=body, timeout=300, headers={
                "Content-Type": "video/mp4", "Content-Range": f"bytes {start}-{end}/{size}"})
            r.raise_for_status()

    publish_id = data["publish_id"]
    for _ in range(60):
        st = _post("/post/publish/status/fetch/", {"publish_id": publish_id})
        status = st.get("status")
        if status == "PUBLISH_COMPLETE":
            ids = st.get("publicaly_available_post_id") or []
            if ids:
                return str(ids[0]), f"https://www.tiktok.com/video/{ids[0]}"
            return publish_id, ""
        if status == "SEND_TO_USER_INBOX":
            return publish_id, ""  # čeka da ga objaviš u aplikaciji
        if status == "FAILED":
            raise RuntimeError(f"TikTok objava nije uspjela: {st.get('fail_reason')}")
        time.sleep(5)
    return publish_id, ""


def stats(ext_id: str) -> dict:
    if not ext_id.isdigit():  # još je skica u inboxu
        return {}
    data = _post("/video/query/", {"filters": {"video_ids": [ext_id]}},
                 fields="id,view_count,like_count,comment_count")
    v = (data.get("videos") or [{}])[0]
    return {"views": v.get("view_count", 0), "likes": v.get("like_count", 0), "comments": v.get("comment_count", 0)}


def followers() -> int:
    r = httpx.get(f"{API}/user/info/", params={"fields": "follower_count"},
                  headers={"Authorization": f"Bearer {_token()}"}, timeout=30)
    return r.json().get("data", {}).get("user", {}).get("follower_count", 0)


def comments(ext_id: str) -> list[dict]:
    return []  # TikTokov javni API ne daje komentare


def reply(comment_id: str, text: str):
    raise NotImplementedError("TikTok API ne podržava odgovaranje na komentare")

