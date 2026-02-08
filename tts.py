import os
import re
import time
from pathlib import Path

from elevenlabs import ElevenLabs
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, ID3NoHeaderError
from mutagen.mp3 import MP3

from config import (
    AUDIO_DIR,
    ELEVENLABS_API_KEY,
    ELEVENLABS_MODEL,
    ELEVENLABS_VOICE_ID,
    TTS_MAX_RETRIES,
    TTS_RATE_LIMIT_SECONDS,
)


def build_tts_text(poem):
    """Build the text sent to ElevenLabs TTS for a poem.

    Collapses all line breaks into spaces so the model reads the poem as
    flowing prose, finding natural pauses from punctuation rather than
    resetting cadence at every line break. A stanza break (double newline)
    separates the intro from the body.
    """
    intro = f'{poem["title"]}, by {poem["author"]}.'
    body = poem["body"]

    # Collapse all whitespace (line breaks, extra spaces) into single spaces
    prose = re.sub(r"\s+", " ", body).strip()

    return f"{intro}\n\n{prose}"


def char_count(poem):
    """Return the character count of the TTS text for a poem."""
    return len(build_tts_text(poem))


def generate_audio(poem, force=False):
    """Generate TTS audio for a single poem. Returns the output path.

    Skips generation if the MP3 already exists unless force=True.
    Uses exponential backoff for retries on API errors.
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    output_path = AUDIO_DIR / f'{poem["slug"]}.mp3'

    if output_path.exists() and not force:
        print(f'  Skipping {poem["slug"]} (already exists)')
        return output_path

    text = build_tts_text(poem)
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    for attempt in range(TTS_MAX_RETRIES):
        try:
            audio_iterator = client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                model_id=ELEVENLABS_MODEL,
                text=text,
            )
            # Collect all audio chunks
            audio_bytes = b"".join(audio_iterator)
            output_path.write_bytes(audio_bytes)
            break
        except Exception as e:
            if attempt < TTS_MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Retry {attempt + 1}/{TTS_MAX_RETRIES} after error: {e}")
                print(f"  Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

    # Tag the MP3 with ID3 metadata
    _tag_mp3(output_path, poem)

    print(f'  Generated {poem["slug"]}.mp3 ({len(audio_bytes)} bytes)')
    return output_path


def _tag_mp3(path, poem):
    """Add ID3 tags to the generated MP3 file."""
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.add(TIT2(encoding=3, text=poem["title"]))
    tags.add(TPE1(encoding=3, text=poem.get("author", "Unknown")))
    tags.add(TALB(encoding=3, text="Poesy"))
    tags.add(TRCK(encoding=3, text=str(poem["index"])))
    tags.save(path)


def get_mp3_duration(path):
    """Return the duration of an MP3 file in seconds."""
    audio = MP3(path)
    return audio.info.length


def generate_all(poems, force=False, dry_run=False):
    """Generate TTS audio for all poems.

    In dry-run mode, prints character counts without calling the API.
    """
    total_chars = 0
    generated = 0

    for poem in poems:
        chars = char_count(poem)
        total_chars += chars
        label = f'{poem["index"]:2d}. {poem["title"]}'

        if dry_run:
            print(f"  {label}: {chars} chars")
            continue

        output_path = AUDIO_DIR / f'{poem["slug"]}.mp3'
        if output_path.exists() and not force:
            print(f"  {label}: skipped (exists)")
            continue

        print(f"  {label}: {chars} chars — generating...")
        generate_audio(poem, force=force)
        generated += 1

        # Rate limiting between API calls
        time.sleep(TTS_RATE_LIMIT_SECONDS)

    print(f"\nTotal: {total_chars} characters across {len(poems)} poems")
    if dry_run:
        print("(dry run — no API calls made)")
    else:
        print(f"Generated {generated} new audio files")
