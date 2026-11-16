"""Pokreće agente u pozadini, u dvije dretve.

produkcija: Scout -> Writer -> Clipper/Editor/Designer (dugotrajno, renderiranje)
operativa:  Publisher (točno u termin), Analyst, Community
"""
import threading
import time
import traceback

from . import db
from .agents import crew, fail, log
from .config import DEMO_MODE

# korak -> stanje videa dok korak radi (ako pukne, taj video ide u "failed")
STEPS = {
    "Scout": (crew.scout, None),
    "Writer": (crew.writer, "writing"),
    "Editor": (crew.produce, "producing"),
    "Publisher": (crew.publisher, "publishing"),
    "Analyst": (crew.analyst, None),
    "Community": (crew.community, None),
}


def _step(agent: str):
    fn, busy_status = STEPS[agent]
    try:
        fn()
    except Exception as e:
        traceback.print_exc()
        msg = f"{type(e).__name__}: {e}"
        fail(agent, msg)
        log(agent, f"Greška: {msg}")
        if busy_status:
            db.run("UPDATE videos SET status='failed', error=?, updated_at=? WHERE status=?",
                   msg[:500], time.time(), busy_status)


def _production(stop: threading.Event):
    while not stop.is_set():
        for agent in ("Scout", "Writer", "Editor"):
            _step(agent)
        stop.wait(3 if DEMO_MODE else 15)


def _operations(stop: threading.Event):
    every = {"Analyst": 20 if DEMO_MODE else 900, "Community": 30 if DEMO_MODE else 600}
    last = {k: 0.0 for k in every}
    while not stop.is_set():
        _step("Publisher")
        for agent, secs in every.items():
            if time.time() - last[agent] >= secs:
                last[agent] = time.time()
                _step(agent)
        stop.wait(5)


def recover():
    """Poslije restarta vrati poluzavršene poslove natrag u red."""
    db.run("UPDATE videos SET status='approved' WHERE status='writing'")
    db.run("UPDATE videos SET status='scripted' WHERE status='producing'")
    # objava je mogla djelomično uspjeti, pa je ne ponavljamo sami
    db.run("UPDATE videos SET status='failed', error='Server je restartan usred objave' WHERE status='publishing'")


def start() -> threading.Event:
    stop = threading.Event()
    recover()
    for target in (_production, _operations):
        threading.Thread(target=target, args=(stop,), daemon=True).start()
    return stop
