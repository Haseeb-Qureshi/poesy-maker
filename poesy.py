#!/usr/bin/env python3
"""Poesy Maker — Generate dramatic AI audio readings of poems as a podcast."""

import argparse
import sys
import warnings

# Suppress pydantic v1 compat warning from elevenlabs on Python 3.14
warnings.filterwarnings("ignore", message="Core Pydantic V1")

from config import ELEVENLABS_API_KEY
from parser import fetch_and_parse, load_poems, save_poems
from tts import generate_all, generate_audio, char_count
from feed import generate_feed


def cmd_fetch(args):
    """Fetch the Google Doc and parse poems into poems.json."""
    print("Fetching Google Doc...")
    poems = fetch_and_parse()
    save_poems(poems)
    print(f"Parsed {len(poems)} poems")


def cmd_list(args):
    """List all parsed poems."""
    poems = load_poems()
    for p in poems:
        author = p["author"] or "(unknown)"
        chars = char_count(p)
        print(f'  {p["index"]:2d}. {p["title"]} — {author} ({chars} chars) [{p["slug"]}]')
    print(f"\n  {len(poems)} poems total")


def cmd_generate(args):
    """Generate TTS audio for poems."""
    if not args.dry_run and not ELEVENLABS_API_KEY:
        print("Error: ELEVENLABS_API_KEY not set in .env")
        sys.exit(1)

    poems = load_poems()

    if args.poem:
        # Find poem by slug or title substring match
        query = args.poem.lower()
        match = [
            p for p in poems
            if query in p["slug"] or query in p["title"].lower()
        ]
        if not match:
            print(f'No poem matching "{args.poem}"')
            sys.exit(1)
        if len(match) > 1:
            print(f'Multiple matches for "{args.poem}":')
            for m in match:
                print(f'  - {m["title"]} [{m["slug"]}]')
            sys.exit(1)
        poems = match

    print(f"Generating audio for {len(poems)} poem(s)...")
    generate_all(poems, force=args.force, dry_run=args.dry_run)


def cmd_feed(args):
    """Generate the podcast RSS feed."""
    poems = load_poems()
    generate_feed(poems)


def cmd_all(args):
    """Run the full pipeline: fetch, generate, feed."""
    cmd_fetch(args)
    cmd_generate(args)
    if not args.dry_run:
        cmd_feed(args)
    else:
        print("\n(Skipping feed generation in dry-run mode)")


def main():
    parser = argparse.ArgumentParser(
        description="Poesy Maker — dramatic AI audio readings of poems"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch
    subparsers.add_parser("fetch", help="Fetch Google Doc and parse poems")

    # list
    subparsers.add_parser("list", help="List all parsed poems")

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate TTS audio")
    gen_parser.add_argument(
        "--poem", help="Generate one poem (by slug or title substring)"
    )
    gen_parser.add_argument(
        "--dry-run", action="store_true", help="Show character counts only"
    )
    gen_parser.add_argument(
        "--force", action="store_true", help="Regenerate even if MP3 exists"
    )

    # feed
    subparsers.add_parser("feed", help="Generate RSS podcast feed")

    # all
    all_parser = subparsers.add_parser("all", help="Run full pipeline")
    all_parser.add_argument(
        "--dry-run", action="store_true", help="Fetch + count chars only"
    )
    all_parser.add_argument(
        "--force", action="store_true", help="Regenerate all audio"
    )
    all_parser.add_argument(
        "--poem", help="Generate one poem (by slug or title substring)"
    )

    args = parser.parse_args()

    commands = {
        "fetch": cmd_fetch,
        "list": cmd_list,
        "generate": cmd_generate,
        "feed": cmd_feed,
        "all": cmd_all,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
