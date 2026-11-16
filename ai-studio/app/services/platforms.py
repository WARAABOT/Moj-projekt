"""Jedno mjesto za sve platforme. U demo načinu objave se samo simuliraju."""
import random
import uuid
from types import SimpleNamespace

from ..config import DEMO_MODE, PLATFORMS
from . import instagram, tiktok, youtube

NAMES = {"youtube": "YouTube Shorts", "tiktok": "TikTok", "instagram": "Instagram Reels"}
_REAL = {"youtube": youtube, "tiktok": tiktok, "instagram": instagram}

_FAKE_COMMENTS = [
    "This is exactly what I needed today", "Can you do a part 2?", "What tool did you use for this?",
    "Saving this for later", "Wait, this actually works??", "Underrated channel fr",
    "I tried it and it saved me an hour", "First!", "How do you find these?",
]


def _demo(name: str):
    def stats(ext_id: str) -> dict:
        r = random.Random(ext_id)
        base = r.randint(800, 9000)
        return {"views": base, "likes": base // r.randint(8, 20), "comments": base // r.randint(80, 200)}

    return SimpleNamespace(
        ready=lambda: True,
        upload=lambda video, title, desc, tags, thumb: (
            (eid := uuid.uuid4().hex[:11]), f"https://example.com/{name}/{eid}"),
        stats=stats,
        followers=lambda: 0,
        comments=lambda ext_id: [
            {"id": uuid.uuid4().hex, "author": f"user{random.randint(100, 999)}", "text": random.choice(_FAKE_COMMENTS)}
        ] if random.random() < 0.5 else [],
        reply=lambda comment_id, text: None,
    )


def get(name: str):
    return _demo(name) if DEMO_MODE else _REAL[name]


def enabled() -> list[str]:
    return [p for p in PLATFORMS if p in _REAL]


def ready() -> list[str]:
    return [p for p in enabled() if get(p).ready()]
