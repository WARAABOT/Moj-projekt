"""Editor: spaja snimke, glas i titlove u video (uspravni 1080x1920 ili vodoravni 1920x1080)."""
import subprocess
from pathlib import Path

from .tts import Word

FPS = 30


def size(landscape: bool) -> tuple[int, int]:
    return (1920, 1080) if landscape else (1080, 1920)


def _ff(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _segment(src: Path, seconds: float, out: Path, landscape: bool):
    W, H = size(landscape)
    # -stream_loop: kratka snimka se ponavlja dok ne pokrije cijelu scenu
    _ff("-stream_loop", "-1", "-i", str(src), "-t", f"{seconds:.3f}", "-an",
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out))


def _ts(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def captions(words: list[Word], out: Path, landscape: bool = False):
    """Kratki: 3 velike riječi na sredini (TikTok stil). Dugi: 7 manjih riječi pri dnu.
    Riječ koja se upravo govori je žuta."""
    W, H = size(landscape)
    per_line, font, outline, margin = (7, 62, 5, 70) if landscape else (3, 108, 7, 560)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter,{font},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},3,2,60,60,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for g in range(0, len(words), per_line):
        group = words[g:g + per_line]
        for i, (_, start, end) in enumerate(group):
            # riječ ostaje istaknuta do početka sljedeće riječi, da tekst ne treperi
            k = g + i + 1
            end = words[k][1] if k < len(words) else end + 0.4
            text = " ".join(
                ("{\\c&H00E5FF&}" + w.upper() + "{\\c&HFFFFFF&}") if j == i else w.upper()
                for j, (w, _, _) in enumerate(group)
            )
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,{text}")
    out.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def render(clips: list[tuple[Path, float]], audio: Path, words: list[Word], workdir: Path, out: Path,
           landscape: bool = False) -> Path:
    """clips: (putanja snimke, trajanje scene u sekundama)."""
    parts = []
    for i, (src, secs) in enumerate(clips):
        seg = workdir / f"seg{i}.mp4"
        _segment(src, secs, seg, landscape)
        parts.append(seg)
    listing = workdir / "list.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    joined = workdir / "joined.mp4"
    _ff("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined))

    ass = workdir / "captions.ass"
    captions(words, ass, landscape)
    # titlovi se prže u sliku; putanja je relativna jer libass ne voli dvotočke u putanjama
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", joined.name, "-i", str(audio.resolve()),
         "-vf", f"ass={ass.name}", "-map", "0:v", "-map", "1:a", "-shortest",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out.resolve())],
        check=True, cwd=workdir,
    )
    return out


def frame(video: Path, at: float, out: Path) -> Path:
    _ff("-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1", str(out))
    return out
