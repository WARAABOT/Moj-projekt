"""Glas (ElevenLabs) s vremenom svake riječi, za titlove."""
import base64
import subprocess
from pathlib import Path

import httpx

from ..config import DEMO_MODE, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

Word = tuple[str, float, float]  # riječ, početak, kraj (sekunde)


def speak(text: str, out: Path) -> tuple[Path, list[Word]]:
    if DEMO_MODE or not ELEVENLABS_API_KEY:
        return _silent(text, out)
    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/with-timestamps",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    out = out.with_suffix(".mp3")
    out.write_bytes(base64.b64decode(data["audio_base64"]))
    a = data["alignment"]
    return out, _chars_to_words(a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"])


def _chars_to_words(chars, starts, ends) -> list[Word]:
    words, cur, s0, e0 = [], "", 0.0, 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append((cur, s0, e0))
            cur = ""
            continue
        if not cur:
            s0 = s
        cur += ch
        e0 = e
    if cur:
        words.append((cur, s0, e0))
    return words


def _silent(text: str, out: Path) -> tuple[Path, list[Word]]:
    """Demo: tišina iste duljine kao govor (~2.7 riječi u sekundi)."""
    words, t = [], 0.3
    for w in text.split():
        d = 0.22 + 0.045 * len(w)
        words.append((w, t, t + d))
        t += d + 0.05
    out = out.with_suffix(".m4a")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{t + 0.5:.2f}", "-c:a", "aac", str(out)],
        check=True,
    )
    return out, words
