"""Sve postavke dolaze iz .env datoteke (vidi .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def flag(name: str, default: bool = False) -> bool:
    return env(name, "1" if default else "0").lower() in ("1", "true", "yes", "da")


DATA_DIR = Path(env("DATA_DIR", str(ROOT / "data")))
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "studio.db"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Pristup ploči
DASHBOARD_USER = env("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = env("DASHBOARD_PASSWORD")
# Javna adresa servera, npr. https://studio.mojadomena.com (Instagram mora preuzeti video s nje)
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL").rstrip("/")

# Kanal
NICHE = env("NICHE", "AI tools and tech tips")
LANGUAGE = env("LANGUAGE", "English")
TIMEZONE = env("TIMEZONE", "Europe/Zagreb")
POST_TIMES = [t.strip() for t in env("POST_TIMES", "09:00,13:00,18:00").split(",") if t.strip()]
VIDEOS_PER_DAY = len(POST_TIMES)
PLATFORMS = [p.strip() for p in env("PLATFORMS", "youtube,tiktok,instagram").split(",") if p.strip()]

# Kad je "true", taj korak ne čeka tvoje odobrenje
AUTO_APPROVE_TOPICS = flag("AUTO_APPROVE_TOPICS")
AUTO_APPROVE_PUBLISH = flag("AUTO_APPROVE_PUBLISH")

# AI servisi
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-opus-5-5")
ELEVENLABS_API_KEY = env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = env("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
PEXELS_API_KEY = env("PEXELS_API_KEY")

# Platforme
YOUTUBE_CLIENT_ID = env("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = env("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = env("YOUTUBE_REFRESH_TOKEN")
YOUTUBE_PRIVACY = env("YOUTUBE_PRIVACY", "public")

TIKTOK_CLIENT_KEY = env("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = env("TIKTOK_CLIENT_SECRET")
# "inbox" = video stiže u TikTok aplikaciju kao skica, "direct" = odmah javno (treba odobren API)
TIKTOK_MODE = env("TIKTOK_MODE", "inbox")
TIKTOK_PRIVACY = env("TIKTOK_PRIVACY", "PUBLIC_TO_EVERYONE")

INSTAGRAM_USER_ID = env("INSTAGRAM_USER_ID")
INSTAGRAM_ACCESS_TOKEN = env("INSTAGRAM_ACCESS_TOKEN")
GRAPH_API = env("GRAPH_API", "https://graph.facebook.com/v21.0")

# Demo način: bez ključeva sve se simulira, da vidiš kako ploča radi
DEMO_MODE = flag("DEMO_MODE", default=not ANTHROPIC_API_KEY)

