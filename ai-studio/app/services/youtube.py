"""YouTube Shorts preko YouTube Data API v3."""
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .. import db
from ..config import YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_PRIVACY, YOUTUBE_REFRESH_TOKEN

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def refresh_token() -> str:
    return db.kv_get("youtube_refresh_token") or YOUTUBE_REFRESH_TOKEN


def ready() -> bool:
    return bool(YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET and refresh_token())


def _api():
    creds = Credentials(None, refresh_token=refresh_token(), token_uri=TOKEN_URL,
                        client_id=YOUTUBE_CLIENT_ID, client_secret=YOUTUBE_CLIENT_SECRET, scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(video: Path, title: str, description: str, tags: list[str], thumb: Path) -> tuple[str, str]:
    body = {
        "snippet": {"title": title[:100], "description": description, "tags": tags, "categoryId": "28"},
        "status": {"privacyStatus": YOUTUBE_PRIVACY, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},  # YouTube traži oznaku za AI sadržaj
    }
    req = _api().videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    try:  # vlastiti thumbnail radi samo na kanalu potvrđenom brojem mobitela (youtube.com/verify)
        _api().thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
    except Exception:
        pass
    return vid, f"https://youtube.com/watch?v={vid}"


def stats(ext_id: str) -> dict:
    items = _api().videos().list(part="statistics", id=ext_id).execute().get("items", [])
    s = items[0]["statistics"] if items else {}
    return {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0))}


def followers() -> int:
    items = _api().channels().list(part="statistics", mine=True).execute().get("items", [])
    return int(items[0]["statistics"].get("subscriberCount", 0)) if items else 0


def comments(ext_id: str) -> list[dict]:
    resp = _api().commentThreads().list(part="snippet", videoId=ext_id, maxResults=20, order="time").execute()
    out = []
    for t in resp.get("items", []):
        top = t["snippet"]["topLevelComment"]
        s = top["snippet"]
        out.append({"id": top["id"], "author": s.get("authorDisplayName", ""), "text": s.get("textOriginal", "")})
    return out


def reply(comment_id: str, text: str):
    _api().comments().insert(part="snippet", body={"snippet": {"parentId": comment_id, "textOriginal": text}}).execute()
