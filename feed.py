import os
from datetime import datetime, timedelta, timezone

from podgen import Category, Episode, Media, Person, Podcast

from config import (
    AUDIO_DIR,
    GITHUB_PAGES_BASE_URL,
    OUTPUT_DIR,
    PODCAST_AUTHOR,
    PODCAST_CATEGORY,
    PODCAST_DESCRIPTION,
    PODCAST_LANGUAGE,
    PODCAST_SUBCATEGORY,
    PODCAST_TITLE,
)
from tts import get_mp3_duration


def generate_feed(poems, season=None):
    """Generate an RSS podcast feed from existing MP3 files.

    Creates one episode per poem with staggered publication dates so
    episodes appear in order in podcast apps.

    If season is specified, only include poems from that season.
    """
    if season is not None:
        poems = [p for p in poems if p.get("season") == season]

    name = PODCAST_TITLE
    if season is not None:
        name = f"{PODCAST_TITLE} — Season {season}"

    podcast = Podcast(
        name=name,
        description=PODCAST_DESCRIPTION,
        language=PODCAST_LANGUAGE,
        authors=[Person(PODCAST_AUTHOR)],
        website=GITHUB_PAGES_BASE_URL,
        category=Category(PODCAST_CATEGORY, PODCAST_SUBCATEGORY),
        explicit=False,
    )

    # Base date: stagger episodes 1 day apart so they sort in order
    base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    episodes_added = 0

    for i, poem in enumerate(poems):
        mp3_path = AUDIO_DIR / f'{poem["slug"]}.mp3'
        if not mp3_path.exists():
            print(f'  Warning: {poem["slug"]}.mp3 not found, skipping')
            continue

        file_size = mp3_path.stat().st_size
        duration = timedelta(seconds=get_mp3_duration(str(mp3_path)))
        audio_url = f'{GITHUB_PAGES_BASE_URL}/output/audio/{poem["slug"]}.mp3'

        episode = Episode(
            title=f'{poem["title"]}',
            summary=f'{poem["title"]} by {poem["author"]}',
            media=Media(
                audio_url,
                size=file_size,
                type="audio/mpeg",
                duration=duration,
            ),
            publication_date=base_date + timedelta(days=i),
        )
        podcast.episodes.append(episode)
        episodes_added += 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    feed_path = OUTPUT_DIR / "feed.xml"
    podcast.rss_file(str(feed_path))
    label = f"season {season}" if season else "all poems"
    print(f"Generated feed with {episodes_added} episodes ({label}) at {feed_path}")
    return feed_path
