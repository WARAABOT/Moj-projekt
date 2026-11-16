"""Glas s vremenom svake riječi (za titlove).

Redom: ElevenLabs (ako upišeš ključ) -> Kokoro (besplatno, radi na serveru) -> tišina (demo).
"""
import base64
import re
import subprocess
import threading
from pathlib import Path

import httpx

from ..config import DATA_DIR, DEMO_MODE, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, env

Word = tuple[str, float, float]  # riječ, početak, kraj (sekunde)

KOKORO_DIR = DATA_DIR / "kokoro"
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_VOICE = env("KOKORO_VOICE", "am_michael")
KOKORO_SPEED = float(env("KOKORO_SPEED", "1.05"))
_kokoro = None
_lock = threading.Lock()


def speak(text: str, out: Path) -> tuple[Path, list[Word]]:
    if DEMO_MODE:
        return _silent(text, out)
    if ELEVENLABS_API_KEY:
        return _elevenlabs(text, out)
    return _kokoro_speak(text, out)


# ---------- Kokoro (besplatno) ----------

def _load_kokoro():
    global _kokoro
    with _lock:
        if _kokoro is None:
            from kokoro_onnx import Kokoro

            KOKORO_DIR.mkdir(parents=True, exist_ok=True)
            for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):  # prvo pokretanje: preuzmi model (~350 MB)
                f = KOKORO_DIR / name
                if not f.exists():
                    tmp = f.with_suffix(".part")
                    with httpx.stream("GET", KOKORO_URL + name, follow_redirects=True, timeout=600) as r:
                        r.raise_for_status()
                        with tmp.open("wb") as fh:
                            for chunk in r.iter_bytes():
                                fh.write(chunk)
                    tmp.rename(f)
            _kokoro = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
    return _kokoro


def _kokoro_speak(text: str, out: Path) -> tuple[Path, list[Word]]:
    import numpy as np
    import soundfile as sf

    k = _load_kokoro()
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    pieces, words, t = [], [], 0.0
    for s in sentences:
        samples, sr = k.create(s, voice=KOKORO_VOICE, speed=KOKORO_SPEED, lang="en-us")
        dur = len(samples) / sr
        # Kokoro ne daje vrijeme svake riječi, pa ga dijelimo po duljini riječi unutar rečenice
        ws = s.split()
        weights = [len(w) + 2 for w in ws]
        total, acc = sum(weights), 0.0
        for w, wt in zip(ws, weights):
            start = t + dur * acc / total
            acc += wt
            words.append((w, start, t + dur * acc / total))
        pause = np.zeros(int(sr * 0.22), dtype=np.float32)
        pieces += [samples, pause]
        t += dur + 0.22
    out = out.with_suffix(".wav")
    sf.write(out, np.concatenate(pieces), sr)
    return out, words


# ---------- ElevenLabs (plaćeno, opcionalno) ----------

def _elevenlabs(text: str, out: Path) -> tuple[Path, list[Word]]:
    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/with-timestamps",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        timeout=600,
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


# ---------- demo ----------

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
