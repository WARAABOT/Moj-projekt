"""Clipper: uspravne snimke s Pexelsa (besplatno), a u demo načinu neonski gradijenti."""
import random
import subprocess
from pathlib import Path

import httpx

from ..config import DEMO_MODE, PEXELS_API_KEY

NEON = ["0xff2bd6", "0x7b2cff", "0x00e5ff", "0xff7a00", "0x18ff8a", "0xffd400"]


def fetch_clip(query: str, out: Path, seconds: float) -> Path:
    if not DEMO_MODE and PEXELS_API_KEY:
        try:
            return _pexels(query, out)
        except Exception:
            pass  # nema rezultata ili greška: koristi gradijent da video ipak nastane
    return _gradient(out, seconds)


def _pexels(query: str, out: Path) -> Path:
    r = httpx.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 8},
        timeout=30,
    )
    r.raise_for_status()
    videos = r.json().get("videos", [])
    if not videos:
        raise LookupError(query)
    files = [
        f for v in videos[:4] for f in v["video_files"]
        if f.get("height") and f["height"] >= 1280 and f["height"] > f.get("width", 0)
    ]
    if not files:
        raise LookupError(query)
    best = min(files, key=lambda f: abs(f["height"] - 1920))
    out = out.with_suffix(".mp4")
    with httpx.stream("GET", best["link"], timeout=120, follow_redirects=True) as s:
        s.raise_for_status()
        with out.open("wb") as fh:
            for chunk in s.iter_bytes():
                fh.write(chunk)
    return out


def _gradient(out: Path, seconds: float) -> Path:
    c0, c1 = random.sample(NEON, 2)
    out = out.with_suffix(".mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"gradients=s=1080x1920:d={seconds + 1:.2f}:speed=0.015:c0={c0}:c1={c1}:c2=0x0b0618:nb_colors=3",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", str(out)],
        check=True,
    )
    return out
