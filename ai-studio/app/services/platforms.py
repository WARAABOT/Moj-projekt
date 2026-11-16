"""Jedno mjesto za sve platforme. Sve funkcije primaju kanal (ch). U demo načinu objave se simuliraju."""
import random
import uuid
from types import SimpleNamespace

from .. import channels
from ..config import DEMO_MODE
from . import instagram, tiktok, youtube

NAMES = {"youtube": "YouTube", "tiktok": "TikTok", "instagram": "Instagram Reels"}
_REAL = {"youtube": youtube, "tiktok": tiktok, "instagram": instagram}

_FAKE_COMMENTS = [
    "This is exactly what I needed today", "Can you do a part 2?", "What tool did you use for this?",
    "Saving this for later", "Wait, this actually works??", "Underrated channel fr",
    "I tried it and it saved me an hour", "First!", "How do you find these?",
]


def _demo(name: str):
    def stats(ch, ext_id: str) -> dict:
        r = random.Random(ext_id)
        base = r.randint(800, 9000)
        return {"views": base, "likes": base // r.randint(8, 20), "comments": base // r.randint(80, 200)}

    return SimpleNamespace(
        ready=lambda ch: True,
        upload=lambda ch, video, title, desc, tags, thumb: (
            (eid := uuid.uuid4().hex[:11]), f"https://example.com/{name}/{eid}"),
        stats=stats,
        followers=lambda ch: 0,
        comments=lambda ch, ext_id: [
            {"id": uuid.uuid4().hex, "author": f"user{random.randint(100, 999)}", "text": random.choice(_FAKE_COMMENTS)}
        ] if random.random() < 0.5 else [],
        reply=lambda ch, comment_id, text: None,
    )


def get(name: str):
    return _demo(name) if DEMO_MODE else _REAL[name]


def enabled(ch: dict) -> list[str]:
    return [p for p in channels.platform_list(ch) if p in _REAL]


def ready(ch: dict) -> list[str]:
    return [p for p in enabled(ch) if get(p).ready(ch)]
