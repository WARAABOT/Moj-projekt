"""Downloads free stock video clips from Pexels (free API key: pexels.com/api)."""
import os
import random

import requests

API = "https://api.pexels.com/videos/search"


def find_clips(query: str, vertical: bool, count: int, out_dir: str, used: set) -> list[str]:
    r = requests.get(API, timeout=30, headers={"Authorization": os.environ["PEXELS_API_KEY"]},
                     params={"query": query, "per_page": 15,
                             "orientation": "portrait" if vertical else "landscape"})
    r.raise_for_status()
    videos = [v for v in r.json().get("videos", []) if v["id"] not in used]
    random.shuffle(videos)
    paths = []
    for v in videos[:count]:
        files = [f for f in v["video_files"] if f.get("height") and f["file_type"] == "video/mp4"]
        if not files:
            continue
        # smallest file that is still at least 1080p on the short side, else the biggest one
        good = [f for f in files if min(f["width"], f["height"]) >= 1080]
        f = min(good, key=lambda f: f["width"]) if good else max(files, key=lambda f: f["width"])
        path = os.path.join(out_dir, f"clip_{v['id']}.mp4")
        with requests.get(f["link"], stream=True, timeout=120) as d:
            d.raise_for_status()
            with open(path, "wb") as fh:
                for part in d.iter_content(1 << 20):
                    fh.write(part)
        used.add(v["id"])
        paths.append(path)
    return paths
