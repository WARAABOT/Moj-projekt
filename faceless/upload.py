"""Uploads a video (and thumbnail) to YouTube with the Data API v3."""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def youtube(refresh_token: str):
    creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"])
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(refresh_token: str, video: str, meta: dict, privacy: str, thumb: str | None = None) -> str:
    yt = youtube(refresh_token)
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["description"][:4900],
                    "tags": meta["tags"][:30], "categoryId": meta.get("category", "27")},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(video, chunksize=16 << 20, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    video_id = resp["id"]
    if thumb:
        try:  # needs a phone-verified channel; a missing thumbnail is not worth failing the run
            yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb)).execute()
        except Exception as e:
            print(f"  thumbnail not set: {e}")
    return video_id
