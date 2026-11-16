"""Što svaki agent radi. Orkestrator (app/orchestrator.py) ih poziva redom."""
import json
import random
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from .. import db, llm
from ..config import (AUTO_APPROVE_PUBLISH, AUTO_APPROVE_TOPICS, DEMO_MODE, LANGUAGE, LONG_DAYS, LONG_ENABLED,
                      LONG_TIME, MEDIA_DIR, NICHE, POST_TIMES, TIMEZONE, VIDEOS_PER_DAY)
from ..services import media, platforms, render, thumbnail, tts
from . import idle, log, work

IN_FLIGHT = ("idea", "approved", "writing", "scripted", "producing", "review", "scheduled")
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _in_flight(fmt: str) -> int:
    return db.row(f"SELECT COUNT(*) n FROM videos WHERE format=? AND status IN ({','.join('?' * len(IN_FLIGHT))})",
                  fmt, *IN_FLIGHT)["n"]


# ---------- Scout: smišlja teme ----------

class Idea(BaseModel):
    topic: str
    angle: str
    why: str


class Ideas(BaseModel):
    ideas: list[Idea]


DEMO_IDEAS = [
    ("3 free AI tools that replace paid apps", "Show each tool in 10 seconds", "Free tool lists get saved a lot"),
    ("The 5-second prompt trick for better answers", "One before/after example", "Quick wins perform well"),
    ("Why your phone battery dies so fast", "Myth vs fact format", "Evergreen curiosity topic"),
    ("This AI turns sketches into websites", "Live demo feel", "Visual transformation hooks"),
    ("Stop doing this with ChatGPT", "Common mistake + fix", "Negative hooks raise retention"),
    ("How I edit videos 10x faster", "Workflow in 4 steps", "Creators love workflow content"),
    ("The hidden iPhone feature nobody uses", "Step-by-step", "Hidden features get shared"),
    ("AI made this song in 30 seconds", "Reveal at the end", "Surprise endings boost rewatches"),
]
DEMO_LONG_IDEAS = [
    ("15 AI tools that will save you 10 hours a week", "Ranked list with real use cases", "Long lists keep watch time high"),
    ("How AI actually works, explained simply", "From zero to understanding in 10 minutes", "Explainers rank in search"),
    ("I tested every free AI video tool", "Honest comparison with a winner", "Comparisons get strong search traffic"),
]


def scout():
    """Puni red tema: kratki (svaki dan) i dugi YouTube videi (nekoliko tjedno)."""
    pending = db.row("SELECT COUNT(*) n FROM approvals WHERE kind='topic' AND status='pending'")["n"]
    if pending >= 5:
        return
    if _in_flight("short") < VIDEOS_PER_DAY * 2:
        _scout("short")
    if LONG_ENABLED and "youtube" in platforms.enabled() and _in_flight("long") < max(2, len(LONG_DAYS)):
        _scout("long")


def _scout(fmt: str):
    long = fmt == "long"
    work("Scout", "Traži teme za dugi YouTube video" if long else "Traži trending teme", 0.3)
    used = [r["topic"] for r in db.rows("SELECT topic FROM videos ORDER BY id DESC LIMIT 40")]
    if DEMO_MODE:
        time.sleep(2)
        pool = DEMO_LONG_IDEAS if long else DEMO_IDEAS
        fresh = [i for i in pool if i[0] not in used] or pool
        ideas = [Idea(topic=t, angle=a, why=w) for t, a, w in random.sample(fresh, min(2 if long else 3, len(fresh)))]
    else:
        best = db.rows("""SELECT v.title, v.format, SUM(p.views) views FROM videos v JOIN posts p ON p.video_id=v.id
                          GROUP BY v.id ORDER BY views DESC LIMIT 8""")
        kind = ("2 ideas for 8-12 minute horizontal YouTube videos (educational, lists, comparisons, explainers) "
                "that work with voiceover and stock footage and that people search for on YouTube"
                if long else
                "3 ideas for 30-45 second vertical videos (TikTok, Shorts, Reels) with a strong hook")
        ideas = llm.ask(
            "You are a video strategist for a faceless channel (voiceover + stock footage + captions).",
            f"Channel niche: {NICHE}. Video language: {LANGUAGE}.\n"
            f"Our best videos so far: {json.dumps(best)}\n"
            f"Topics already used, do not repeat: {json.dumps(used)}\n"
            f"Suggest {kind}.",
            Ideas,
        ).ideas
    for i in ideas:
        status = "approved" if AUTO_APPROVE_TOPICS else "idea"
        vid = db.insert("videos", topic=i.topic, angle=i.angle, status=status, format=fmt,
                        created_at=time.time(), updated_at=time.time())
        if status == "idea":
            db.insert("approvals", kind="topic", ref_id=vid,
                      title=("[DUGI] " if long else "") + i.topic,
                      detail=f"{i.angle}. {i.why}", created_at=time.time())
    log("Scout", f"Predlaže {len(ideas)} {'dugih' if long else 'kratkih'} tema")
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
                  description=f"{topic} - tips every day.", hashtags=["ai", "tech", "tips"])


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
    long = v["format"] == "long"
    db.update_video(v["id"], status="writing")
    work("Writer", f"Piše {'dugi ' if long else ''}scenarij: {v['topic']}", 0.4)
    if DEMO_MODE:
        time.sleep(3)
        s = _demo_script(v["topic"], long)
    else:
        s = llm.ask(
            "You write scripts for a faceless video channel. Spoken language, punchy, no emojis in narration.",
            f"Topic: {v['topic']}\nAngle: {v['angle']}\nLanguage: {LANGUAGE}\n"
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
    log("Writer", f"Scenarij gotov: {s.title} ({words} riječi)")
    idle("Writer")


# ---------- Clipper + Editor + Designer: izrada videa ----------

def _duration(path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def _stamp(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def produce():
    v = db.row("SELECT * FROM videos WHERE status='scripted' ORDER BY id LIMIT 1")
    if not v:
        return
    vid, long = v["id"], v["format"] == "long"
    db.update_video(vid, status="producing")
    script = Script(**db.video_script(v))
    scenes = script.scenes()
    folder = MEDIA_DIR / f"v{vid}-{uuid.uuid4().hex[:8]}"
    work_dir = folder / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. glas
    work("Editor", "Snima glas", 0.1)
    audio, words = tts.speak(" ".join(s.narration for s in scenes), work_dir / "voice")
    total = _duration(audio)
    log("Editor", f"Glas gotov ({_stamp(total)})")

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
        work("Clipper", f"Traži snimku {k + 1}/{len(scenes)}: {s.visual}", (k + 1) / len(scenes))
        clips.append((media.fetch_clip(s.visual, work_dir / f"clip{k}", d, landscape=long), d))
    log("Clipper", f"Pronašao {len(clips)} snimki")
    idle("Clipper")

    # 4. montaža s titlovima
    work("Editor", f"Montira {'dugi ' if long else ''}video ({_stamp(total)})", 0.6)
    final = folder / f"{uuid.uuid4().hex}.mp4"
    render.render(clips, audio, words, work_dir, final, landscape=long)
    idle("Editor")
    log("Editor", f"Video gotov: {script.title}")

    # 5. poglavlja u opisu (YouTube ih sam pretvori u oznake na traci)
    description = script.description
    if long and len(script.chapters) >= 3:
        lines, k = [], 0
        for ch in script.chapters:
            lines.append(f"{_stamp(bounds[k])} {ch.title}")
            k += len(ch.scenes)
        description += "\n\nChapters:\n" + "\n".join(lines)

    # 6. naslovna slika
    work("Designer", f"Radi thumbnail: {script.thumbnail_text}", 0.5)
    shot = render.frame(work_dir / "joined.mp4", min(1.5, total / 3), work_dir / "frame.jpg")  # bez titlova
    thumb = thumbnail.make(shot, script.thumbnail_text, folder / f"{uuid.uuid4().hex}.jpg", landscape=long)
    idle("Designer")
    log("Designer", "Thumbnail gotov")
    shutil.rmtree(work_dir, ignore_errors=True)

    db.update_video(vid, status="review", description=description,
                    video_path=final.relative_to(MEDIA_DIR).as_posix(),
                    thumb_path=thumb.relative_to(MEDIA_DIR).as_posix())
    if AUTO_APPROVE_PUBLISH:
        schedule(vid)
    else:
        where = "YouTube (dugi video)" if long else ", ".join(platforms.NAMES[p] for p in platforms.enabled())
        db.insert("approvals", kind="publish", ref_id=vid, title=script.title,
                  detail=f"{_stamp(total)} · objava na: {where}", created_at=time.time())


def targets(fmt: str) -> list[str]:
    ready = platforms.ready()
    return [p for p in ready if p == "youtube"] if fmt == "long" else ready


# ---------- raspored ----------

def next_slot(fmt: str = "short") -> float:
    taken = {round(r["scheduled_at"]) for r in db.rows(
        "SELECT scheduled_at FROM videos WHERE status IN ('scheduled','publishing') AND scheduled_at IS NOT NULL")}
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
            if WEEKDAYS[d.weekday()] not in LONG_DAYS:
                continue
            times = [LONG_TIME]
        else:
            times = sorted(POST_TIMES)
        for hm in times:
            h, m = map(int, hm.split(":"))
            slot = datetime(d.year, d.month, d.day, h, m, tzinfo=tz).timestamp()
            if slot > now.timestamp() + 60 and round(slot) not in taken:
                return slot
    return now.timestamp() + 3600


def schedule(vid: int):
    v = db.row("SELECT format FROM videos WHERE id=?", vid)
    at = next_slot(v["format"] if v else "short")
    db.update_video(vid, status="scheduled", scheduled_at=at)
    when = datetime.fromtimestamp(at, ZoneInfo(TIMEZONE)).strftime("%d.%m. u %H:%M")
    log("Publisher", f"Zakazano za {when}")


# ---------- Publisher ----------

def publisher():
    v = db.row("SELECT * FROM videos WHERE status='scheduled' AND scheduled_at<=? ORDER BY scheduled_at LIMIT 1",
               time.time())
    if not v:
        return
    db.update_video(v["id"], status="publishing")
    video, thumb = MEDIA_DIR / v["video_path"], MEDIA_DIR / v["thumb_path"]
    tags = [t for t in (v["hashtags"] or "").split(",") if t]
    ok = 0
    targets_ = targets(v["format"])
    for k, name in enumerate(targets_):
        work("Publisher", f"Objavljuje na {platforms.NAMES[name]}", (k + 0.5) / len(targets_))
        post = db.insert("posts", video_id=v["id"], platform=name, status="uploading")
        try:
            if DEMO_MODE:
                time.sleep(2)
            ext_id, url = platforms.get(name).upload(video, v["title"], v["description"] or "", tags, thumb)
            db.update("posts", post, status="live", external_id=ext_id, url=url, published_at=time.time())
            log("Publisher", f"Objavljeno na {platforms.NAMES[name]}: {v['title']}")
            ok += 1
        except Exception as e:
            db.update("posts", post, status="failed", error=str(e)[:500])
            log("Publisher", f"{platforms.NAMES[name]} greška: {e}")
    if not targets_:
        log("Publisher", "Nijedna platforma nije povezana")
    db.update_video(v["id"], status="published" if ok else "failed",
                    error=None if ok else "Objava nije uspjela ni na jednoj platformi")
    idle("Publisher", "Čeka sljedeći termin")


# ---------- Analyst ----------

def analyst():
    work("Analyst", "Skuplja preglede i lajkove", 0.5)
    posts = db.rows("SELECT * FROM posts WHERE status='live' AND published_at > ?", time.time() - 30 * 86400)
    for p in posts:
        try:
            s = platforms.get(p["platform"]).stats(p["external_id"])
            if DEMO_MODE:  # simulirani rast
                grow = 1 + random.random() * 0.25
                s = {"views": int(max(p["views"], 50) * grow), "likes": int(max(p["likes"], 3) * grow),
                     "comments": int(max(p["comments"], 1) * grow)}
            if s:
                db.update("posts", p["id"], **s)
        except Exception as e:
            log("Analyst", f"Statistika {p['platform']}: {e}")
    for name in platforms.ready():
        views = db.row("SELECT COALESCE(SUM(views),0) n FROM posts WHERE platform=?", name)["n"]
        try:
            fol = platforms.get(name).followers()
            if DEMO_MODE:
                last = db.row("SELECT followers FROM stats WHERE platform=? ORDER BY ts DESC LIMIT 1", name)
                fol = (last["followers"] if last else random.randint(9000, 40000)) + random.randint(0, 25)
        except Exception:
            fol = 0
        db.insert("stats", ts=time.time(), platform=name, views=views, followers=fol)
    idle("Analyst", f"Prati {len(posts)} objava")


# ---------- Community ----------

class Reply(BaseModel):
    id: int
    reply: str
    skip: bool


class Replies(BaseModel):
    replies: list[Reply]


def community():
    work("Community", "Čita nove komentare", 0.3)
    posts = db.rows("""SELECT * FROM posts WHERE status='live' AND platform IN ('youtube','instagram')
                       AND published_at > ? ORDER BY published_at DESC LIMIT 15""", time.time() - 7 * 86400)
    for p in posts:
        try:
            for c in platforms.get(p["platform"]).comments(p["external_id"]):
                db.run("""INSERT OR IGNORE INTO comments (platform, post_id, external_id, author, text, status, ts)
                          VALUES (?,?,?,?,?, 'new', ?)""", p["platform"], p["id"], c["id"], c["author"], c["text"], time.time())
        except Exception as e:
            log("Community", f"Komentari {p['platform']}: {e}")

    new = db.rows("SELECT id, text FROM comments WHERE status='new' LIMIT 10")
    if new:
        work("Community", f"Piše odgovore na {len(new)} komentara", 0.7)
        if DEMO_MODE:
            replies = [Reply(id=c["id"], reply="Thanks! Part 2 is coming this week 🙌", skip=False) for c in new]
        else:
            replies = llm.ask(
                "You manage comments for a short-form video channel. Friendly, short, human replies.",
                f"Language: {LANGUAGE}. For each comment write a reply (max 25 words). Set skip=true for spam, "
                f"hate or comments that need no reply.\nComments: {json.dumps(new)}",
                Replies,
            ).replies
        by_id = {r.id: r for r in replies}
        for c in new:
            r = by_id.get(c["id"])
            if not r or r.skip:
                db.run("UPDATE comments SET status='ignored' WHERE id=?", c["id"])
                continue
            db.run("UPDATE comments SET status='suggested', reply=? WHERE id=?", r.reply, c["id"])
            db.insert("approvals", kind="reply", ref_id=c["id"], title=f"Odgovor: “{c['text'][:60]}”",
                      detail=r.reply, created_at=time.time())
        log("Community", f"Predložio {len(new)} odgovora")
    idle("Community", "Prati komentare")


# ---------- tvoje odobrenje ----------

def decide(approval_id: int, approve: bool, edited_text: str | None = None):
    a = db.row("SELECT * FROM approvals WHERE id=? AND status='pending'", approval_id)
    if not a:
        return
    db.update("approvals", approval_id, status="approved" if approve else "rejected")
    if a["kind"] == "topic":
        db.update_video(a["ref_id"], status="approved" if approve else "rejected")
        log("Scout", f"Tema {'odobrena' if approve else 'odbijena'}: {a['title']}")
    elif a["kind"] == "publish":
        if approve:
            schedule(a["ref_id"])
        else:
            db.update_video(a["ref_id"], status="rejected")
    elif a["kind"] == "reply":
        c = db.row("SELECT c.*, p.platform FROM comments c JOIN posts p ON p.id=c.post_id WHERE c.id=?", a["ref_id"])
        if c and approve:
            text = edited_text or c["reply"]
            platforms.get(c["platform"]).reply(c["external_id"], text)
            db.run("UPDATE comments SET status='replied', reply=? WHERE id=?", text, c["id"])
            log("Community", f"Odgovorio @{c['author']}")
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
