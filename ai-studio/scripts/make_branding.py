"""Izradi logo i bannere u mapi branding/ (isto radi gumb "Napravi logo i banner" na ploči).

Pokretanje: python scripts/make_branding.py "Byte Crew" "AI tools & tech tips · new videos every day" "#ff2bd6"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.branding import build  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "Byte Crew"
tagline = sys.argv[2] if len(sys.argv) > 2 else "AI tools & tech tips · new videos every day"
color = (sys.argv[3] if len(sys.argv) > 3 else "#ff2bd6").lstrip("#")
accent = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
for label, path in build(Path(__file__).resolve().parent.parent / "branding", name, tagline, accent).items():
    print(f"{label}: {path}")
