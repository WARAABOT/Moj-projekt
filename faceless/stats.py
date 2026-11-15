"""Saves views/likes/subscribers per channel to stats/<channel>.json so the daily planner can learn."""
import datetime as dt
import json
import os
import pathlib

from .upload import youtube

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    for hist_file in sorted((ROOT / "history").glob("*.json")):
        cid = hist_file.stem
        token = os.environ.get(f"YT_TOKEN_{cid.upper()}")
        if not token:
            continue
        history = {h["video_id"]: h for h in json.loads(hist_file.read_text()) if h.get("video_id")}
        try:
            yt = youtube(token)
            ch = yt.channels().list(part="statistics", mine=True).execute()["items"][0]["statistics"]
            videos, ids = [], list(history)
            for i in range(0, len(ids), 50):
                for v in yt.videos().list(part="statistics,status", id=",".join(ids[i:i + 50])).execute()["items"]:
                    h, s = history[v["id"]], v["statistics"]
                    videos.append({"id": v["id"], "date": h["date"], "format": h["format"], "title": h["title"],
                                   "privacy": v["status"]["privacyStatus"],
                                   **{k: int(s.get(k + "Count", 0)) for k in ("view", "like", "comment")}})
        except Exception as e:  # e.g. an old token without the readonly permission
            print(f"[{cid}] stats failed: {e}")
            continue
        out = {"updated": dt.date.today().isoformat(),
               "channel": {k: int(ch.get(k, 0)) for k in ("subscriberCount", "viewCount", "videoCount")},
               "videos": videos}
        (ROOT / "stats").mkdir(exist_ok=True)
        (ROOT / "stats" / f"{cid}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"[{cid}] {out['channel']}")


if __name__ == "__main__":
    main()
