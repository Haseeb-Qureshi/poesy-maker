import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
AUDIO_DIR = OUTPUT_DIR / "audio"
POEMS_JSON = PROJECT_ROOT / "poems.json"
AUTHORS_JSON = PROJECT_ROOT / "authors.json"

# Google Doc
GOOGLE_DOC_ID = "14sDs0p_Xp1rEz1sxipZt7lolUs1ZM6SWTin08Uq96j0"
GOOGLE_DOC_EXPORT_URL = (
    f"https://docs.google.com/document/d/{GOOGLE_DOC_ID}/export?format=txt"
)

# ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL = "eleven_multilingual_v2"
# Daniel — British, deep male voice, good for dramatic poetry
ELEVENLABS_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"

# Podcast metadata
PODCAST_TITLE = "Poesy"
PODCAST_DESCRIPTION = "Dramatic AI readings of great poems, for memorization."
PODCAST_AUTHOR = "Poesy Maker"
PODCAST_LANGUAGE = "en"
PODCAST_CATEGORY = "Arts"
PODCAST_SUBCATEGORY = "Books"

# GitHub Pages (custom domain via haseebq.com)
GITHUB_PAGES_BASE_URL = "https://haseebq.com/poesy-maker"

# TTS settings
TTS_RATE_LIMIT_SECONDS = 1.0
TTS_MAX_RETRIES = 3
