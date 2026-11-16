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
from ..config import (AUTO_APPROVE_PUBLISH, AUTO_APPROVE_TOPICS, DEMO_MODE, LANGUAGE, MEDIA_DIR, NICHE,
                      POST_TIMES, TIMEZONE, VIDEOS_PER_DAY)
from ..services import media, platforms, render, thumbnail, tts
from . import idle, log, work

IN_FLIGHT = ("idea", "approved", "writing", "scripted", "producing", "review", "scheduled")


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


def scout():
    active = db.row(f"SELECT COUNT(*) n FROM videos WHERE status IN ({','.join('?' * len(IN_FLIGHT))})", *IN_FLIGHT)["n"]
    pending = db.row("SELECT COUNT(*) n FROM approvals WHERE kind='topic' AND status='pending'")["n"]
    if active >= VIDEOS_PER_DAY * 2 or pending >= 4:
        return
    work("Scout", "Traži trending teme", 0.3)
    if DEMO_MODE:
        time.sleep(2)
        used = {r["topic"] for r in db.rows("SELECT topic FROM videos")}
        fresh = [i for i in DEMO_IDEAS if i[0] not in used] or DEMO_IDEAS
        picks = random.sample(fresh, min(3, len(fresh)))
        ideas = [Idea(topic=t, angle=a, why=w) for t, a, w in picks]
    else:
        best = db.rows("""SELECT v.title, SUM(p.views) views FROM videos v JOIN posts p ON p.video_id=v.id
                          GROUP BY v.id ORDER BY views DESC LIMIT 5""")
        recent = [r["topic"] for r in db.rows("SELECT topic FROM videos ORDER BY id DESC LIMIT 30")]
        ideas = llm.ask(
            "You are a short-form video strategist for TikTok, YouTube Shorts and Instagram Reels.",
            f"Channel niche: {NICHE}. Video language: {LANGUAGE}.\n"
            f"Our best videos so far (title, views): {json.dumps(best)}\n"
            f"Topics already used, do not repeat: {json.dumps(recent)}\n"
            "Suggest 3 new video ideas for 30-45 second vertical videos that can be made with voiceover, "
            "stock footage and captions (no on-camera person). Each needs a strong hook.",
            Ideas,
        ).ideas
    for i in ideas:
        status = "approved" if AUTO_APPROVE_TOPICS else "idea"
        vid = db.insert("videos", topic=i.topic, angle=i.angle, status=status,
                        created_at=time.time(), updated_at=time.time())
        if status == "idea":
            db.insert("approvals", kind="topic", ref_id=vid, title=i.topic,
                      detail=f"{i.angle}. {i.why}", created_at=time.time())
    log("Scout", f"Predlaže {len(ideas)} nove teme")
    idle("Scout", "Prati trendove")


# ---------- Writer: scenarij ----------

class Scene(BaseModel):
    narration: str
    visual: str


class Script(BaseModel):
    title: str
    thumbnail_text: str
    scenes: list[Scene]
    description: str
    hashtags: list[str]


def _demo_script(topic: str) -> Script:
    return Script(
        title=topic, thumbnail_text=" ".join(topic.split()[:4]),
        scenes=[
            Scene(narration=f"{topic}. Stay until the end, the last one is the best.", visual="neon city night"),
            Scene(narration="Number one. It takes ten seconds to set up and it is completely free.", visual="laptop typing"),
            Scene(narration="Number two. Most people never notice this, but it changes everything.", visual="smartphone closeup"),
            Scene(narration="And number three. Follow for more tips like this every day.", visual="abstract technology"),
        ],
        description=f"{topic} - quick tips every day.", hashtags=["ai", "tech", "tips", "shorts"],
    )


def writer():
    v = db.row("SELECT * FROM videos WHERE status='approved' ORDER BY id LIMIT 1")
    if not v:
        return
    db.update_video(v["id"], status="writing")
    work("Writer", f"Piše scenarij: {v['topic']}", 0.4)
    if DEMO_MODE:
        time.sleep(3)
        s = _demo_script(v["topic"])
    else:
        s = llm.ask(
            "You write viral short-form video scripts. Spoken, punchy, no filler, no emojis in narration.",
            f"Topic: {v['topic']}\nAngle: {v['angle']}\nLanguage: {LANGUAGE}\n"
            "Write a 30-45 second voiceover script split into 4-7 scenes. The first scene is the hook "
            "and must grab attention in the first 2 seconds. For every scene give `visual`: a 2-4 word "
            "English search query for vertical stock footage. Also give a title (max 70 chars), "
            "thumbnail_text (max 5 words), a 1-2 sentence description and 3-6 hashtags without '#'.",
            Script, effort="medium",
        )
    db.update_video(v["id"], status="scripted", script=s.model_dump_json(), title=s.title,
                    description=s.description, hashtags=",".join(s.hashtags))
    log("Writer", f"Scenarij gotov: {s.title} ({sum(len(x.narration.split()) for x in s.scenes)} riječi)")
    idle("Writer")


# ---------- Clipper + Editor + Designer: izrada videa ----------

def _duration(path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def produce():
    v = db.row("SELECT * FROM videos WHERE status='scripted' ORDER BY id LIMIT 1")
    if not v:
        return
    vid = v["id"]
    db.update_video(vid, status="producing")
    script = Script(**db.video_script(v))
    folder = MEDIA_DIR / f"v{vid}-{uuid.uuid4().hex[:8]}"
    work_dir = folder / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. glas
    work("Editor", "Snima glas", 0.1)
    narration = " ".join(s.narration for s in script.scenes)
    audio, words = tts.speak(narration, work_dir / "voice")
    total = _duration(audio)
    log("Editor", f"Glas gotov ({total:.0f} s)")

    # 2. podjela riječi po scenama -> trajanje svake scene
    bounds, i = [], 0
    for s in script.scenes:
        n = len(s.narration.split())
        bounds.append(words[i][1] if i < len(words) else total)
        i += n
    bounds[0] = 0.0
    bounds.append(total)
    durations = [max(0.5, bounds[k + 1] - bounds[k]) for k in range(len(script.scenes))]

    # 3. snimke
    clips = []
    for k, (s, d) in enumerate(zip(script.scenes, durations)):
        work("Clipper", f"Traži snimku: {s.visual}", (k + 1) / len(script.scenes))
        clips.append((media.fetch_clip(s.visual, work_dir / f"clip{k}", d), d))
    log("Clipper", f"Pronašao {len(clips)} snimki")
    idle("Clipper")

    # 4. montaža s titlovima
    work("Editor", "Montira i dodaje titlove", 0.6)
    final = folder / f"{uuid.uuid4().hex}.mp4"
    render.render(clips, audio, words, work_dir, final)
    idle("Editor")
    log("Editor", f"Video gotov: {script.title}")

    # 5. naslovna slika
    work("Designer", f"Radi thumbnail: {script.thumbnail_text}", 0.5)
    shot = render.frame(work_dir / "joined.mp4", min(1.5, total / 3), work_dir / "frame.jpg")  # bez titlova
    thumb = thumbnail.make(shot, script.thumbnail_text, folder / f"{uuid.uuid4().hex}.jpg")
    idle("Designer")
    log("Designer", "Thumbnail gotov")
    shutil.rmtree(work_dir, ignore_errors=True)

    db.update_video(vid, status="review",
                    video_path=final.relative_to(MEDIA_DIR).as_posix(),
                    thumb_path=thumb.relative_to(MEDIA_DIR).as_posix())
    if AUTO_APPROVE_PUBLISH:
        schedule(vid)
    else:
        db.insert("approvals", kind="publish", ref_id=vid, title=script.title,
                  detail=f"Objava na: {', '.join(platforms.NAMES[p] for p in platforms.enabled())}",
                  created_at=time.time())


# ---------- raspored ----------

def next_slot() -> float:
    taken = {round(r["scheduled_at"]) for r in db.rows(
        "SELECT scheduled_at FROM videos WHERE status IN ('scheduled','publishing') AND scheduled_at IS NOT NULL")}
    if DEMO_MODE:  # u demu ne čekamo do sutra
        t = time.time() + 45
        while any(abs(t - x) < 40 for x in taken):
            t += 45
        return t
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    for day in range(30):
        d = (now + timedelta(days=day)).date()
        for hm in sorted(POST_TIMES):
            h, m = map(int, hm.split(":"))
            slot = datetime(d.year, d.month, d.day, h, m, tzinfo=tz).timestamp()
            if slot > now.timestamp() + 60 and round(slot) not in taken:
                return slot
    return now.timestamp() + 3600


def schedule(vid: int):
    at = next_slot()
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
    targets = platforms.ready()
    for k, name in enumerate(targets):
        work("Publisher", f"Objavljuje na {platforms.NAMES[name]}", (k + 0.5) / len(targets))
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
    if not targets:
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
