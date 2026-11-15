"""Makes (and uploads) today's videos.

    python -m faceless.main                      # every channel, formats picked by the schedule
    python -m faceless.main --channel gta6 --format short --no-upload
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import tomllib
import traceback

from . import footage, render, upload, voice, write

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOOTER = "\n\nNarration: AI voice. Stock footage: Pexels."


def make_video(cid: str, channel: dict, fmt: str, today: dt.date, do_upload: bool) -> dict:
    hist_file = ROOT / "history" / f"{cid}.json"
    history = json.loads(hist_file.read_text()) if hist_file.exists() else []
    work = ROOT / "output" / cid / f"{today}-{fmt}"
    work.mkdir(parents=True, exist_ok=True)

    print(f"[{cid}/{fmt}] writing script")
    meta = write.write_script(channel, fmt, [h["topic"] for h in history], today.isoformat())
    (work / "script.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"[{cid}/{fmt}] {meta['title']} ({len(meta['scenes'])} scenes)")

    used, scenes = set(), []
    for i, sc in enumerate(meta["scenes"]):
        audio = str(work / f"voice_{i:03d}.mp3")
        words = voice.speak(sc["narration"], channel["voice"], audio)
        secs = render.duration(audio)
        try:
            clips = footage.find_clips(sc["footage_query"], fmt == "short",
                                       max(1, min(3, round(secs / 7))), str(work), used)
        except Exception as e:
            print(f"  no footage for '{sc['footage_query']}': {e}")
            clips = []
        scenes.append({"audio": audio, "words": words, "clips": clips})

    print(f"[{cid}/{fmt}] rendering")
    video = render.assemble(scenes, fmt, str(work))
    thumb = render.thumbnail(str(work), meta["thumbnail_text"]) if fmt == "long" else None

    meta["category"] = channel.get("category", "27")
    meta["description"] += FOOTER
    if fmt == "short" and "#shorts" not in meta["title"].lower():
        meta["title"] = meta["title"][:90] + " #Shorts"

    video_id = None
    token = os.environ.get(f"YT_TOKEN_{cid.upper()}")
    if do_upload and token:
        print(f"[{cid}/{fmt}] uploading")
        video_id = upload.upload(token, video, meta, os.environ.get("YT_PRIVACY", "private"), thumb)
        print(f"[{cid}/{fmt}] https://youtu.be/{video_id}")
    else:
        print(f"[{cid}/{fmt}] not uploaded (no YT_TOKEN_{cid.upper()} or --no-upload): {video}")

    for p in work.glob("*"):  # keep only what a person might want to download
        if p.name not in {"final.mp4", "thumbnail.jpg", "script.json"}:
            p.unlink()
    history.append({"date": today.isoformat(), "format": fmt, "topic": meta["topic"],
                    "title": meta["title"], "video_id": video_id})
    hist_file.parent.mkdir(exist_ok=True)
    hist_file.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="all", help="channel file name without .toml, or 'all'")
    ap.add_argument("--format", default="auto", choices=["auto", "short", "long", "both"])
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    today = dt.date.today()
    files = sorted((ROOT / "channels").glob("*.toml"))
    if args.channel != "all":
        files = [f for f in files if f.stem == args.channel]
        if not files:
            raise SystemExit(f"unknown channel {args.channel}")

    failed = []
    for f in files:
        channel = tomllib.loads(f.read_text())
        if args.format == "auto":
            fmts = ["short"] + (["long"] if today.weekday() in channel.get("long_days", []) else [])
        else:
            fmts = ["short", "long"] if args.format == "both" else [args.format]
        for fmt in fmts:
            try:
                make_video(f.stem, channel, fmt, today, not args.no_upload)
            except Exception:
                traceback.print_exc()
                failed.append(f"{f.stem}/{fmt}")
    if failed:
        raise SystemExit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
