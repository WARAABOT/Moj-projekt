"""Builds the final video with ffmpeg: stock clips + voice + burned-in captions, and a thumbnail."""
import os
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_NAME = "DejaVu Sans"
PAUSE = 0.25  # seconds of silence after each scene
SIZES = {"short": (1080, 1920), "long": (1920, 1080)}


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


def scene_video(clips: list[str], dur: float, size, out: str, cwd: str):
    w, h = size
    fit = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,setsar=1"
    if not clips:  # nothing found: plain dark background
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x101018:s={w}x{h}:r=30", "-t", f"{dur:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", out], cwd)
        return
    part = dur / len(clips)
    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-stream_loop", "-1", "-t", f"{part:.3f}", "-i", c]
    chains = "".join(f"[{i}:v]{fit}[v{i}];" for i in range(len(clips)))
    joins = "".join(f"[v{i}]" for i in range(len(clips)))
    cmd += ["-filter_complex", f"{chains}{joins}concat=n={len(clips)}:v=1:a=0[out]", "-map", "[out]",
            "-t", f"{dur:.3f}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", out]
    run(cmd, cwd)


def _ts(s: float) -> str:
    cs = int(round(s * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def captions(words: list[tuple[float, float, str]], fmt: str, out: str):
    w, h = SIZES[fmt]
    if fmt == "short":  # big centered words, TikTok style
        style, per = f"{FONT_NAME},96,&H0000F0FF,&H00000000,1,7,4,5,60,60,0", 3
    else:
        style, per = f"{FONT_NAME},64,&H00FFFFFF,&H00000000,1,4,2,2,120,120,70", 7
    name, size, primary, outline, bold, border, shadow, align, ml, mr, mv = style.split(",")
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
             "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
             f"Style: Default,{name},{size},{primary},{outline},&H80000000,{bold},1,{border},{shadow},"
             f"{align},{ml},{mr},{mv}", "",
             "[Events]", "Format: Layer, Start, End, Style, Text"]
    for i in range(0, len(words), per):
        group = words[i:i + per]
        text = " ".join(t for _, _, t in group)
        end = words[i + per][0] if i + per < len(words) else group[-1][1]
        lines.append(f"Dialogue: 0,{_ts(group[0][0])},{_ts(end)},Default,"
                     f"{text.upper() if fmt == 'short' else text}")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def assemble(scenes: list[dict], fmt: str, work: str) -> str:
    """scenes: [{audio, words, clips}] -> path of final mp4 (inside work)."""
    size = SIZES[fmt]
    t, all_words, seg_list, audio_inputs = 0.0, [], [], []
    for i, s in enumerate(scenes):
        dur = duration(s["audio"]) + PAUSE
        seg = f"seg_{i:03d}.mp4"
        scene_video(s["clips"], dur, size, seg, work)
        seg_list.append(f"file '{seg}'")
        audio_inputs += ["-i", s["audio"]]
        all_words += [(a + t, b + t, w) for a, b, w in s["words"]]
        t += dur
    with open(os.path.join(work, "segments.txt"), "w") as f:
        f.write("\n".join(seg_list) + "\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "segments.txt", "-c", "copy", "video.mp4"], work)

    n = len(scenes)
    pads = "".join(f"[{i}:a]aresample=48000,apad=pad_dur={PAUSE}[a{i}];" for i in range(n))
    joins = "".join(f"[a{i}]" for i in range(n))
    run(["ffmpeg", "-y", *audio_inputs, "-filter_complex", f"{pads}{joins}concat=n={n}:v=0:a=1[out]",
         "-map", "[out]", "voice.wav"], work)

    captions(all_words, fmt, os.path.join(work, "captions.ass"))
    run(["ffmpeg", "-y", "-i", "video.mp4", "-i", "voice.wav", "-vf", "ass=captions.ass",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", "final.mp4"], work)
    return os.path.join(work, "final.mp4")


def thumbnail(work: str, text: str) -> str:
    """1280x720 frame from the clean video with big text on top."""
    frame = os.path.join(work, "frame.jpg")
    run(["ffmpeg", "-y", "-ss", f"{duration(os.path.join(work, 'video.mp4')) * 0.3:.2f}",
         "-i", "video.mp4", "-frames:v", "1", "frame.jpg"], work)
    img = Image.open(frame).convert("RGB")
    scale = max(1280 / img.width, 720 / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)))
    left, top = (img.width - 1280) // 2, (img.height - 720) // 2
    img = ImageEnhance.Brightness(img.crop((left, top, left + 1280, top + 720))).enhance(0.6)
    draw = ImageDraw.Draw(img)
    text = "\n".join(textwrap.wrap(text.upper(), 14)[:3])
    size = 150
    while size > 60:
        font = ImageFont.truetype(FONT_FILE, size)
        box = draw.multiline_textbbox((0, 0), text, font=font, stroke_width=8, spacing=10)
        if box[2] - box[0] <= 1180 and box[3] - box[1] <= 620:
            break
        size -= 8
    draw.multiline_text((640, 360), text, font=font, fill=(255, 230, 0), anchor="mm", align="center",
                        stroke_width=8, stroke_fill=(0, 0, 0), spacing=10)
    out = os.path.join(work, "thumbnail.jpg")
    img.save(out, quality=90)
    return out
