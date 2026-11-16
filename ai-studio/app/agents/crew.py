"""Što svaki agent radi. Orkestrator (app/orchestrator.py) ih poziva redom.

Agenti su zajednički za sve kanale: jedan tim radi za sve profile, a svaki video pripada jednom kanalu.
"""
import json
import random
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from .. import channels, db, llm
from ..config import DEMO_MODE, MEDIA_DIR, TIMEZONE
from ..services import media, platforms, render, thumbnail, tts
from . import idle, log, work

IN_FLIGHT = ("idea", "approved", "writing", "scripted", "producing", "review", "scheduled")
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _in_flight(cid: int, fmt: str) -> int:
    return db.row(f"""SELECT COUNT(*) n FROM videos WHERE channel_id=? AND format=?
                      AND status IN ({','.join('?' * len(IN_FLIGHT))})""", cid, fmt, *IN_FLIGHT)["n"]


def _channel(v: dict) -> dict:
    ch = channels.get(v["channel_id"])
    if not ch:
        raise LookupError(f"Kanal {v['channel_id']} ne postoji")
    return ch


# ---------- Scout: smišlja teme ----------

class Idea(BaseModel):
    topic: str
    angle: str
    why: str


class Ideas(BaseModel):
    ideas: list[Idea]


DEMO_SHORT = ["3 {n} mistakes everyone makes", "The {n} trick nobody talks about", "Stop doing this with {n}",
              "{n} in 30 seconds", "Why {n} is harder than it looks", "The best free {n} hack",
              "I tried the viral {n} tip", "One {n} habit that changes everything"]
DEMO_LONG = ["The complete beginner's guide to {n}", "15 {n} tips that actually work",
             "I tested every popular {n} method", "{n}: everything you need to know"]


def scout():
    """Za svaki aktivni kanal puni red tema: kratki (svaki dan) i dugi YouTube videi (nekoliko tjedno)."""
    for ch in channels.all(active_only=True):
        pending = db.row("SELECT COUNT(*) n FROM approvals WHERE channel_id=? AND kind='topic' AND status='pending'",
                         ch["id"])["n"]
        if pending >= 5:
            continue
        if _in_flight(ch["id"], "short") < len(channels.post_times(ch)) * 2:
            _scout(ch, "short")
        if ch["long_enabled"] and "youtube" in platforms.enabled(ch) and \
                _in_flight(ch["id"], "long") < max(2, len(channels.long_days(ch))):
            _scout(ch, "long")


def _scout(ch: dict, fmt: str):
    long = fmt == "long"
    work("Scout", f"[{ch['name']}] traži teme za {'dugi video' if long else 'kratke videe'}", 0.3)
    used = [r["topic"] for r in db.rows("SELECT topic FROM videos WHERE channel_id=? ORDER BY id DESC LIMIT 40",
                                        ch["id"])]
    if DEMO_MODE:
        time.sleep(2)
        pool = [t.format(n=ch["niche"] or ch["name"]) for t in (DEMO_LONG if long else DEMO_SHORT)]
        fresh = [t for t in pool if t not in used] or pool
        ideas = [Idea(topic=t, angle="Simple and practical", why="Demo idea")
                 for t in random.sample(fresh, min(2 if long else 3, len(fresh)))]
    else:
        best = db.rows("""SELECT v.title, v.format, SUM(p.views) views FROM videos v JOIN posts p ON p.video_id=v.id
                          WHERE v.channel_id=? GROUP BY v.id ORDER BY views DESC LIMIT 8""", ch["id"])
        kind = ("2 ideas for 8-12 minute horizontal YouTube videos (educational, lists, comparisons, explainers) "
                "that work with voiceover and stock footage and that people search for on YouTube"
                if long else
                "3 ideas for 30-45 second vertical videos (TikTok, Shorts, Reels) with a strong hook")
        ideas = llm.ask(
            "You are a video strategist for a faceless channel (voiceover + stock footage + captions).",
            f"Channel name: {ch['name']}. Channel niche: {ch['niche']}. Video language: {ch['language']}.\n"
            f"Our best videos so far: {json.dumps(best)}\n"
            f"Topics already used, do not repeat: {json.dumps(used)}\n"
            f"Suggest {kind}.",
            Ideas,
        ).ideas
    for i in ideas:
        status = "approved" if ch["auto_topics"] else "idea"
        vid = db.insert("videos", channel_id=ch["id"], topic=i.topic, angle=i.angle, status=status, format=fmt,
                        created_at=time.time(), updated_at=time.time())
        if status == "idea":
            db.insert("approvals", channel_id=ch["id"], kind="topic", ref_id=vid,
                      title=("[DUGI] " if long else "") + i.topic,
                      detail=f"{i.angle}. {i.why}", created_at=time.time())
    log("Scout", f"Predlaže {len(ideas)} {'dugih' if long else 'kratkih'} tema", ch["id"])
    idle("Scout", "Prati trendove")


# ---------- Writer: scenarij ----------

class Scene(BaseModel):
    narration: str
    visual: str


class Chapter(BaseModel):
    title: str
    scenes: list[Scene]


class Script(BaseModel):
    title: str
    thumbnail_text: str
    chapters: list[Chapter]  # kratki video ima jedno poglavlje
    description: str
    hashtags: list[str]

    def scenes(self) -> list[Scene]:
        return [sc for ch in self.chapters for sc in ch.scenes]


def _demo_script(topic: str, long: bool) -> Script:
    if long:
        chapters = [Chapter(title=t, scenes=[
            Scene(narration=f"{t}. " + "Here is what most people get wrong, and how to fix it in a few simple steps. " * 2,
                  visual=q) for q in ("technology office", "laptop screen")])
            for t in ("Intro", "The basics", "Best tools", "Common mistakes", "Final tips")]
    else:
        chapters = [Chapter(title="Short", scenes=[
            Scene(narration=f"{topic}. Stay until the end, the last one is the best.", visual="neon city night"),
            Scene(narration="Number one. It takes ten seconds to set up and it is completely free.", visual="laptop typing"),
            Scene(narration="Number two. Most people never notice this, but it changes everything.", visual="smartphone closeup"),
            Scene(narration="And number three. Follow for more tips like this every day.", visual="abstract technology"),
        ])]
    return Script(title=topic, thumbnail_text=" ".join(topic.split()[:4]), chapters=chapters,
                  description=f"{topic} - tips every day.", hashtags=["tips", "howto", "learn"])


SHORT_BRIEF = (
    "Write a 30-45 second voiceover script with exactly one chapter titled 'Short', split into 4-7 scenes. "
    "The first scene is the hook and must grab attention in the first 2 seconds. "
)
LONG_BRIEF = (
    "Write a 8-12 minute YouTube voiceover script (about 1400-1800 words in total). Structure it as 6-10 "
    "chapters: the first chapter is 'Intro' with a strong hook and a promise of what the viewer will learn, "
    "the last chapter wraps up and asks to subscribe. Each chapter has 2-6 scenes of 2-5 sentences. "
    "Be specific and genuinely useful, no filler. "
)


def writer():
    v = db.row("SELECT * FROM videos WHERE status='approved' ORDER BY id LIMIT 1")
    if not v:
        return
    ch = _channel(v)
    long = v["format"] == "long"
    db.update_video(v["id"], status="writing")
    work("Writer", f"[{ch['name']}] piše {'dugi ' if long else ''}scenarij: {v['topic']}", 0.4)
    if DEMO_MODE:
        time.sleep(3)
        s = _demo_script(v["topic"], long)
    else:
        s = llm.ask(
            "You write scripts for a faceless video channel. Spoken language, punchy, no emojis in narration.",
            f"Channel: {ch['name']} ({ch['niche']})\nTopic: {v['topic']}\nAngle: {v['angle']}\n"
            f"Language: {ch['language']}\n"
            + (LONG_BRIEF if long else SHORT_BRIEF)
            + "For every scene give `visual`: a 2-4 word English search query for "
            + ("horizontal" if long else "vertical")
            + " stock footage. Also give a title (max 70 chars), thumbnail_text (max 5 words), "
            + ("a 3-4 sentence description" if long else "a 1-2 sentence description")
            + " and 3-8 hashtags without '#'.",
            Script, effort="medium", important=long,
        )
    words = sum(len(x.narration.split()) for x in s.scenes())
    db.update_video(v["id"], status="scripted", script=s.model_dump_json(), title=s.title,
                    description=s.description, hashtags=",".join(h.lstrip("#") for h in s.hashtags))
    log("Writer", f"Scenarij gotov: {s.title} ({words} riječi)", ch["id"])
    idle("Writer")


# ---------- Clipper + Editor + Designer: izrada videa ----------

def _duration(path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def _stamp(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = (hex_color or "#ff2bd6").lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def produce():
    v = db.row("SELECT * FROM videos WHERE status='scripted' ORDER BY id LIMIT 1")
    if not v:
        return
    ch = _channel(v)
    vid, cid, long = v["id"], ch["id"], v["format"] == "long"
    db.update_video(vid, status="producing")
    script = Script(**db.video_script(v))
    scenes = script.scenes()
    folder = MEDIA_DIR / f"c{cid}-v{vid}-{uuid.uuid4().hex[:8]}"
    work_dir = folder / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. glas
    work("Editor", f"[{ch['name']}] snima glas", 0.1)
    audio, words = tts.speak(" ".join(s.narration for s in scenes), work_dir / "voice", ch["voice"])
    total = _duration(audio)
    log("Editor", f"Glas gotov ({_stamp(total)})", cid)

    # 2. podjela riječi po scenama -> trajanje svake scene
    bounds, i = [], 0
    for s in scenes:
        bounds.append(words[i][1] if i < len(words) else total)
        i += len(s.narration.split())
    bounds[0] = 0.0
    bounds.append(total)
    durations = [max(0.5, bounds[k + 1] - bounds[k]) for k in range(len(scenes))]

    # 3. snimke
    clips = []
    for k, (s, d) in enumerate(zip(scenes, durations)):
        work("Clipper", f"[{ch['name']}] snimka {k + 1}/{len(scenes)}: {s.visual}", (k + 1) / len(scenes))
        clips.append((media.fetch_clip(s.visual, work_dir / f"clip{k}", d, landscape=long), d))
    log("Clipper", f"Pronašao {len(clips)} snimki", cid)
    idle("Clipper")

    # 4. montaža s titlovima
    work("Editor", f"[{ch['name']}] montira {'dugi ' if long else ''}video ({_stamp(total)})", 0.6)
    final = folder / f"{uuid.uuid4().hex}.mp4"
    render.render(clips, audio, words, work_dir, final, landscape=long)
    idle("Editor")
    log("Editor", f"Video gotov: {script.title}", cid)

    # 5. poglavlja u opisu (YouTube ih sam pretvori u oznake na traci)
    description = script.description
    if long and len(script.chapters) >= 3:
        lines, k = [], 0
        for chap in script.chapters:
            lines.append(f"{_stamp(bounds[k])} {chap.title}")
            k += len(chap.scenes)
        description += "\n\nChapters:\n" + "\n".join(lines)

    # 6. naslovna slika u boji kanala
    work("Designer", f"[{ch['name']}] thumbnail: {script.thumbnail_text}", 0.5)
    shot = render.frame(work_dir / "joined.mp4", min(1.5, total / 3), work_dir / "frame.jpg")  # bez titlova
    thumb = thumbnail.make(shot, script.thumbnail_text, folder / f"{uuid.uuid4().hex}.jpg", landscape=long,
                           accent=_rgb(ch["color"]))
    idle("Designer")
    log("Designer", "Thumbnail gotov", cid)
    shutil.rmtree(work_dir, ignore_errors=True)

    db.update_video(vid, status="review", description=description,
                    video_path=final.relative_to(MEDIA_DIR).as_posix(),
                    thumb_path=thumb.relative_to(MEDIA_DIR).as_posix())
    if ch["auto_publish"]:
        schedule(vid)
    else:
        where = "YouTube (dugi video)" if long else ", ".join(platforms.NAMES[p] for p in platforms.enabled(ch))
        db.insert("approvals", channel_id=cid, kind="publish", ref_id=vid, title=script.title,
                  detail=f"{_stamp(total)} · objava na: {where}", created_at=time.time())


def targets(ch: dict, fmt: str) -> list[str]:
    ready = platforms.ready(ch)
    return [p for p in ready if p == "youtube"] if fmt == "long" else ready


# ---------- raspored (svaki kanal ima svoje termine) ----------

def next_slot(ch: dict, fmt: str = "short") -> float:
    taken = {round(r["scheduled_at"]) for r in db.rows(
        """SELECT scheduled_at FROM videos WHERE channel_id=? AND status IN ('scheduled','publishing')
           AND scheduled_at IS NOT NULL""", ch["id"])}
    if DEMO_MODE:  # u demu ne čekamo do sutra
        t = time.time() + 45
        while any(abs(t - x) < 40 for x in taken):
            t += 45
        return t
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    for day in range(60):
        d = (now + timedelta(days=day)).date()
        if fmt == "long":
            if WEEKDAYS[d.weekday()] not in channels.long_days(ch):
                continue
            times = [ch["long_time"] or "17:00"]
        else:
            times = channels.post_times(ch)
        for hm in times:
            h, m = map(int, hm.split(":"))
            slot = datetime(d.year, d.month, d.day, h, m, tzinfo=tz).timestamp()
            if slot > now.timestamp() + 60 and round(slot) not in taken:
                return slot
    return now.timestamp() + 3600


def schedule(vid: int):
    v = db.row("SELECT * FROM videos WHERE id=?", vid)
    ch = _channel(v)
    at = next_slot(ch, v["format"])
    db.update_video(vid, status="scheduled", scheduled_at=at)
    when = datetime.fromtimestamp(at, ZoneInfo(TIMEZONE)).strftime("%d.%m. u %H:%M")
    log("Publisher", f"Zakazano za {when}: {v['title']}", ch["id"])


# ---------- Publisher ----------

def publisher():
    v = db.row("SELECT * FROM videos WHERE status='scheduled' AND scheduled_at<=? ORDER BY scheduled_at LIMIT 1",
               time.time())
    if not v:
        return
    ch = _channel(v)
    db.update_video(v["id"], status="publishing")
    video, thumb = MEDIA_DIR / v["video_path"], MEDIA_DIR / v["thumb_path"]
    tags = [t for t in (v["hashtags"] or "").split(",") if t]
    ok = 0
    names = targets(ch, v["format"])
    for k, name in enumerate(names):
        work("Publisher", f"[{ch['name']}] objavljuje na {platforms.NAMES[name]}", (k + 0.5) / len(names))
        post = db.insert("posts", video_id=v["id"], platform=name, status="uploading")
        try:
            if DEMO_MODE:
                time.sleep(2)
            ext_id, url = platforms.get(name).upload(ch, video, v["title"], v["description"] or "", tags, thumb)
            db.update("posts", post, status="live", external_id=ext_id, url=url, published_at=time.time())
            log("Publisher", f"Objavljeno na {platforms.NAMES[name]}: {v['title']}", ch["id"])
            ok += 1
        except Exception as e:
            db.update("posts", post, status="failed", error=str(e)[:500])
            log("Publisher", f"{platforms.NAMES[name]} greška: {e}", ch["id"])
    if not names:
        log("Publisher", "Nijedna platforma nije povezana", ch["id"])
    db.update_video(v["id"], status="published" if ok else "failed",
                    error=None if ok else "Objava nije uspjela ni na jednoj platformi")
    idle("Publisher", "Čeka sljedeći termin")


# ---------- Analyst ----------

def analyst():
    work("Analyst", "Skuplja preglede i lajkove", 0.5)
    total = 0
    for ch in channels.all():
        posts = db.rows("""SELECT p.* FROM posts p JOIN videos v ON v.id=p.video_id
                           WHERE v.channel_id=? AND p.status='live' AND p.published_at > ?""",
                        ch["id"], time.time() - 30 * 86400)
        total += len(posts)
        for p in posts:
            try:
                s = platforms.get(p["platform"]).stats(ch, p["external_id"])
                if DEMO_MODE:  # simulirani rast
                    grow = 1 + random.random() * 0.25
                    s = {"views": int(max(p["views"], 50) * grow), "likes": int(max(p["likes"], 3) * grow),
                         "comments": int(max(p["comments"], 1) * grow)}
                if s:
                    db.update("posts", p["id"], **s)
            except Exception as e:
                log("Analyst", f"Statistika {p['platform']}: {e}", ch["id"])
        for name in platforms.ready(ch):
            views = db.row("""SELECT COALESCE(SUM(p.views),0) n FROM posts p JOIN videos v ON v.id=p.video_id
                              WHERE v.channel_id=? AND p.platform=?""", ch["id"], name)["n"]
            try:
                fol = platforms.get(name).followers(ch)
                if DEMO_MODE:
                    last = db.row("SELECT followers FROM stats WHERE channel_id=? AND platform=? ORDER BY ts DESC LIMIT 1",
                                  ch["id"], name)
                    fol = (last["followers"] if last else random.randint(2000, 20000)) + random.randint(0, 25)
            except Exception:
                fol = 0
            db.insert("stats", ts=time.time(), channel_id=ch["id"], platform=name, views=views, followers=fol)
    idle("Analyst", f"Prati {total} objava")


# ---------- Community ----------

class Reply(BaseModel):
    id: int
    reply: str
    skip: bool


class Replies(BaseModel):
    replies: list[Reply]


def community():
    work("Community", "Čita nove komentare", 0.3)
    for ch in channels.all():
        posts = db.rows("""SELECT p.* FROM posts p JOIN videos v ON v.id=p.video_id
                           WHERE v.channel_id=? AND p.status='live' AND p.platform IN ('youtube','instagram')
                           AND p.published_at > ? ORDER BY p.published_at DESC LIMIT 15""",
                        ch["id"], time.time() - 7 * 86400)
        for p in posts:
            try:
                for c in platforms.get(p["platform"]).comments(ch, p["external_id"]):
                    db.run("""INSERT OR IGNORE INTO comments (platform, post_id, external_id, author, text, status, ts)
                              VALUES (?,?,?,?,?, 'new', ?)""",
                           p["platform"], p["id"], c["id"], c["author"], c["text"], time.time())
            except Exception as e:
                log("Community", f"Komentari {p['platform']}: {e}", ch["id"])

        new = db.rows("""SELECT c.id, c.text FROM comments c JOIN posts p ON p.id=c.post_id JOIN videos v ON v.id=p.video_id
                         WHERE v.channel_id=? AND c.status='new' LIMIT 10""", ch["id"])
        if not new:
            continue
        work("Community", f"[{ch['name']}] piše odgovore na {len(new)} komentara", 0.7)
        if DEMO_MODE:
            replies = [Reply(id=c["id"], reply="Thanks! Part 2 is coming this week 🙌", skip=False) for c in new]
        else:
            replies = llm.ask(
                f"You manage comments for the video channel '{ch['name']}' about {ch['niche']}. "
                "Friendly, short, human replies.",
                f"Language: {ch['language']}. For each comment write a reply (max 25 words). Set skip=true for "
                f"spam, hate or comments that need no reply.\nComments: {json.dumps(new)}",
                Replies,
            ).replies
        by_id = {r.id: r for r in replies}
        for c in new:
            r = by_id.get(c["id"])
            if not r or r.skip:
                db.run("UPDATE comments SET status='ignored' WHERE id=?", c["id"])
                continue
            db.run("UPDATE comments SET status='suggested', reply=? WHERE id=?", r.reply, c["id"])
            db.insert("approvals", channel_id=ch["id"], kind="reply", ref_id=c["id"],
                      title=f"Odgovor: “{c['text'][:60]}”", detail=r.reply, created_at=time.time())
        log("Community", f"Predložio {len(new)} odgovora", ch["id"])
    idle("Community", "Prati komentare")


# ---------- tvoje odobrenje ----------

def decide(approval_id: int, approve: bool, edited_text: str | None = None):
    a = db.row("SELECT * FROM approvals WHERE id=? AND status='pending'", approval_id)
    if not a:
        return
    db.update("approvals", approval_id, status="approved" if approve else "rejected")
    cid = a["channel_id"]
    if a["kind"] == "topic":
        db.update_video(a["ref_id"], status="approved" if approve else "rejected")
        log("Scout", f"Tema {'odobrena' if approve else 'odbijena'}: {a['title']}", cid)
    elif a["kind"] == "publish":
        if approve:
            schedule(a["ref_id"])
        else:
            db.update_video(a["ref_id"], status="rejected")
    elif a["kind"] == "reply":
        c = db.row("SELECT c.*, p.platform FROM comments c JOIN posts p ON p.id=c.post_id WHERE c.id=?", a["ref_id"])
        if c and approve:
            text = edited_text or c["reply"]
            platforms.get(c["platform"]).reply(channels.get(cid), c["external_id"], text)
            db.run("UPDATE comments SET status='replied', reply=? WHERE id=?", text, c["id"])
            log("Community", f"Odgovorio @{c['author']}", cid)
        elif c:
            db.run("UPDATE comments SET status='ignored' WHERE id=?", c["id"])


def retry(vid: int):
    v = db.row("SELECT * FROM videos WHERE id=? AND status='failed'", vid)
    if not v:
        return
    if v["video_path"]:
        schedule(vid)
    else:
        db.update_video(vid, status="scripted" if v["script"] else "approved", error=None)
