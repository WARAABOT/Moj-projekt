"""Text to speech with free Microsoft Edge voices, plus word timings for captions."""
import asyncio

import edge_tts


async def _speak(text: str, voice: str, out: str):
    words = []
    com = edge_tts.Communicate(text, voice, rate="+5%", boundary="WordBoundary")
    with open(out, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":  # offsets are in 100 ns units
                start = chunk["offset"] / 1e7
                words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
    return words


def speak(text: str, voice: str, out: str) -> list[tuple[float, float, str]]:
    for attempt in range(3):
        try:
            return asyncio.run(_speak(text, voice, out))
        except Exception:
            if attempt == 2:
                raise
