"""Instagram Reels preko Instagram Graph API.

Instagram sam preuzima video s javne adrese tvog servera (PUBLIC_BASE_URL/media/...).
"""
import time
from pathlib import Path

import httpx

from ..config import GRAPH_API, MEDIA_DIR, PUBLIC_BASE_URL


# svaki kanal ima svoj Instagram ID i token (upisuju se na ploči, u postavkama kanala)
def ready(ch: dict) -> bool:
    return bool(ch.get("ig_token") and ch.get("ig_user_id") and PUBLIC_BASE_URL)


def _call(ch: dict, method: str, path: str, **params) -> dict:
    params["access_token"] = ch["ig_token"]
    r = httpx.request(method, f"{GRAPH_API}/{path}", params=params, timeout=60)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Instagram: {data['error'].get('message')}")
    return data


def _public_url(p: Path) -> str:
    return f"{PUBLIC_BASE_URL}/media/{p.resolve().relative_to(MEDIA_DIR.resolve()).as_posix()}"


def upload(ch: dict, video: Path, title: str, description: str, tags: list[str], thumb: Path) -> tuple[str, str]:
    caption = f"{title}\n\n{description}\n\n{' '.join('#' + t for t in tags)}"[:2200]
    container = _call(ch, "POST", f"{ch['ig_user_id']}/media", media_type="REELS", video_url=_public_url(video),
                      cover_url=_public_url(thumb), caption=caption, share_to_feed="true")["id"]
    for _ in range(60):  # Instagram obrađuje video do nekoliko minuta
        status = _call(ch, "GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram nije obradio video ({status})")
        time.sleep(10)
    else:
        raise TimeoutError("Instagram obrada traje predugo")
    media_id = _call(ch, "POST", f"{ch['ig_user_id']}/media_publish", creation_id=container)["id"]
    link = _call(ch, "GET", media_id, fields="permalink").get("permalink", "")
    return media_id, link


def stats(ch: dict, ext_id: str) -> dict:
    m = _call(ch, "GET", ext_id, fields="like_count,comments_count")
    views = 0
    try:
        ins = _call(ch, "GET", f"{ext_id}/insights", metric="views")
        views = ins["data"][0]["values"][0]["value"]
    except Exception:
        pass
    return {"views": views, "likes": m.get("like_count", 0), "comments": m.get("comments_count", 0)}


def followers(ch: dict) -> int:
    return _call(ch, "GET", ch["ig_user_id"], fields="followers_count").get("followers_count", 0)


def comments(ch: dict, ext_id: str) -> list[dict]:
    data = _call(ch, "GET", f"{ext_id}/comments", fields="id,text,username").get("data", [])
    return [{"id": c["id"], "author": c.get("username", ""), "text": c.get("text", "")} for c in data]


def reply(ch: dict, comment_id: str, text: str):
    _call(ch, "POST", f"{comment_id}/replies", message=text)
