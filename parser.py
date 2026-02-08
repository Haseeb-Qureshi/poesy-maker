import json
import re
import unicodedata
import requests
from config import GOOGLE_DOC_EXPORT_URL, POEMS_JSON, AUTHORS_JSON


def fetch_doc_text():
    """Fetch the Google Doc as plain text."""
    resp = requests.get(GOOGLE_DOC_EXPORT_URL)
    resp.raise_for_status()
    # Remove BOM and normalize line endings
    text = resp.text.lstrip("\ufeff").replace("\r\n", "\n")
    return text


def slugify(text):
    """Convert text to a URL-safe slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def split_poems(text):
    """Split document text into raw poem chunks on underscore separators.

    Also handles cases where two poems appear in a single chunk separated by
    a trailing '--Author' attribution followed by blank lines and a new title.
    """
    chunks = re.split(r"\n_{4,}\n?", text)
    chunks = [c.strip() for c in chunks if c.strip()]

    # Post-process: split chunks that contain --Author mid-chunk
    # Pattern: "--Author\n\n\nNew Title\nBy Author..." means two poems in one chunk
    result = []
    for chunk in chunks:
        sub = _split_on_trailing_author(chunk)
        result.extend(sub)
    return result


def _split_on_trailing_author(chunk):
    """Split a chunk if it contains a --Author line followed by another poem."""
    # Look for pattern: line starting with --, then 2+ blank lines, then more content
    match = re.search(r"^(--\s*.+)$\n(\s*\n){2,}", chunk, re.MULTILINE)
    if match:
        split_pos = match.end()
        first = chunk[:split_pos].strip()
        rest = chunk[split_pos:].strip()
        if first and rest:
            # Recursively split the rest in case there are more
            return [first] + _split_on_trailing_author(rest)
    return [chunk]


def parse_poem_chunk(raw):
    """Parse a single raw poem chunk into title, author, and body.

    Handles several formats found in the Google Doc:
    - "Title\\nBy Author\\n\\nBody..."
    - "Title\\nby Author\\n\\nBody..."
    - "Title\\nAuthor Name\\n\\nBody..." (known author names)
    - "Author Name\\nTitle\\n\\nBody..." (reversed order)
    - "Title\\n...\\n--Author" (author at end of poem)
    - "from Title\\nBy Author\\nTranslated By Translator\\n\\nBody..."
    """
    lines = raw.split("\n")

    # Strip leading/trailing blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return None

    title = None
    author = None
    body_start = 0

    # Check for trailing --Author attribution
    trailing_author = None
    last_line = lines[-1].strip()
    trailing_match = re.match(r"^--\s*(.+)$", last_line)
    if trailing_match:
        trailing_author = trailing_match.group(1).strip()
        lines = lines[:-1]
        # Strip trailing blanks again
        while lines and not lines[-1].strip():
            lines.pop()

    # First line is always (part of) the title
    first_line = lines[0].strip()

    # Check if second line starts with "By " or "by "
    if len(lines) > 1:
        second_line = lines[1].strip()
        by_match = re.match(r"^[Bb]y\s+(.+)$", second_line)

        if by_match:
            title = first_line
            author = by_match.group(1).strip()
            body_start = 2
            # Check for "Translated By" on next line (skip it, keep original author)
            if len(lines) > 2 and re.match(
                r"^[Tt]ranslated\s+[Bb]y\s+", lines[2].strip()
            ):
                body_start = 3
        elif _is_known_author(second_line):
            # "Title\nAuthor Name" format (author without "By")
            title = first_line
            author = second_line
            body_start = 2
        elif _is_known_author(first_line) and not _is_known_author(second_line):
            # Reversed: "Author\nTitle" format (e.g., Amiri Baraka)
            author = first_line
            title = second_line
            body_start = 2
        else:
            # No author detected on line 2 — title is first line
            title = first_line
            body_start = 1

    else:
        title = first_line
        body_start = 1

    # Use trailing author if we didn't find one in the header
    if not author and trailing_author:
        author = trailing_author

    # Extract body: everything after the header lines, stripped of leading blanks
    body_lines = lines[body_start:]
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)

    body = "\n".join(body_lines)

    return {
        "title": title,
        "author": author,
        "body": body,
    }


# Known author names that appear without "By" prefix in the document
_KNOWN_AUTHORS = {
    "Paul Celan",
    "Mary Oliver",
    "Amiri Baraka",
    "Rabia al-Basri",
    "Constantine P. Cavafy",
    "Ingeborg Bachmann",
    "Yehuda Amichai",
    "Pablo Neruda",
    "Stephen Dobyns",
    "Anne Sexton",
    "Delmore Schwartz",
}


def _is_known_author(text):
    """Check if text matches a known author name."""
    text = text.strip()
    # Also match names in parentheses like "Rabia al-Basri (Rabia al- Adawiyya)"
    base = re.sub(r"\s*\(.*\)\s*$", "", text)
    return base in _KNOWN_AUTHORS


def load_author_overrides():
    """Load manual author overrides from authors.json."""
    try:
        with open(AUTHORS_JSON) as f:
            data = json.load(f)
        return data.get("overrides", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def fetch_and_parse():
    """Fetch the Google Doc and parse all poems. Returns list of poem dicts."""
    text = fetch_doc_text()
    chunks = split_poems(text)
    overrides = load_author_overrides()

    poems = []
    for i, chunk in enumerate(chunks):
        parsed = parse_poem_chunk(chunk)
        if not parsed:
            continue

        slug = slugify(parsed["title"])

        # Apply manual author override if present
        if slug in overrides:
            parsed["author"] = overrides[slug]

        poems.append(
            {
                "index": i + 1,
                "title": parsed["title"],
                "author": parsed["author"],
                "slug": slug,
                "body": parsed["body"],
            }
        )

    return poems


def save_poems(poems):
    """Cache parsed poems to poems.json."""
    with open(POEMS_JSON, "w") as f:
        json.dump(poems, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(poems)} poems to {POEMS_JSON}")


def load_poems():
    """Load poems from cached poems.json."""
    with open(POEMS_JSON) as f:
        return json.load(f)
