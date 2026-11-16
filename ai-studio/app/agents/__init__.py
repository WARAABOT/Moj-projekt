"""Tim agenata: tko je tko i pomoćne funkcije za stanje i dnevnik."""
import time

from .. import db

TEAM = [
    ("Scout", "Trendovi"),
    ("Writer", "Scenariji"),
    ("Clipper", "Snimke"),
    ("Editor", "Glas i montaža"),
    ("Designer", "Thumbnailovi"),
    ("Publisher", "Objave"),
    ("Analyst", "Statistika"),
    ("Community", "Komentari"),
]


def init_team():
    for name, role in TEAM:
        db.run(
            "INSERT OR IGNORE INTO agents (name, role, state, task, progress, updated_at) VALUES (?,?,?,?,?,?)",
            name, role, "idle", "Čeka posao", 0, time.time(),
        )
    # Nakon restarta nitko nije usred posla
    db.run("UPDATE agents SET state='idle', task='Čeka posao', progress=0 WHERE state='working'")


def work(agent: str, task: str, progress: float = 0):
    db.run("UPDATE agents SET state='working', task=?, progress=?, updated_at=? WHERE name=?",
           task, progress, time.time(), agent)


def idle(agent: str, task: str = "Čeka posao"):
    db.run("UPDATE agents SET state='idle', task=?, progress=0, updated_at=? WHERE name=?",
           task, time.time(), agent)


def fail(agent: str, task: str):
    db.run("UPDATE agents SET state='error', task=?, progress=0, updated_at=? WHERE name=?",
           task[:120], time.time(), agent)


def log(agent: str, message: str, channel_id: int | None = None):
    db.insert("events", ts=time.time(), agent=agent, message=message[:300], channel_id=channel_id)
