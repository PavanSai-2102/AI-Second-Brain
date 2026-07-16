"""
SecondSelf — Capture Pipeline (Phase 1: The Archivist)

One command to capture any note, link, or file into raw/ with a timestamp
and unique ID. Supports deduplication via content hashing.

Usage:
    python capture.py note "My brilliant idea about AI agents"
    python capture.py note "Quick thought" --title "AI Agents Idea"
    python capture.py link "https://example.com/article"
    python capture.py file "./documents/research.pdf"
    python capture.py auto "https://example.com"
    python capture.py list
    python capture.py list --type note
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

import config


# ──────────────────────────────────────────────
# 1.1.1 — ID Generation
# ──────────────────────────────────────────────

def generate_id() -> str:
    """
    Generate a unique capture ID.
    Format: cap_YYYYMMDD_<8-char-hex>
    
    Example: cap_20260716_a3f8b2c1
    """
    date_str = datetime.now().strftime("%Y%m%d")
    hex_str = uuid.uuid4().hex[:8]
    return f"cap_{date_str}_{hex_str}"


# ──────────────────────────────────────────────
# 1.1.2 — Content Hashing
# ──────────────────────────────────────────────

def compute_hash(content: str) -> str:
    """
    Compute SHA-256 hash of content string for deduplication.
    
    Returns: "sha256:<hex_digest>"
    """
    normalized = content.strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


# ──────────────────────────────────────────────
# 1.1.3 — Duplicate Detection
# ──────────────────────────────────────────────

def check_duplicate(content_hash: str) -> str | None:
    """
    Scan all existing JSON files in raw/ and compare content_hash.
    
    Returns: The ID of the duplicate capture if found, None otherwise.
    """
    raw_dir = config.RAW_DIR
    if not raw_dir.exists():
        return None

    for json_file in raw_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing_hash = data.get("metadata", {}).get("content_hash", "")
            if existing_hash == content_hash:
                return data.get("id", json_file.stem)
        except (json.JSONDecodeError, OSError):
            # Skip corrupted files
            continue

    return None


# ──────────────────────────────────────────────
# Helper — Sanitize filename
# ──────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Remove special characters from filename, keep it filesystem-safe."""
    # Replace spaces with underscores, remove non-alphanumeric except . - _
    name = re.sub(r'[^\w.\-]', '_', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


# ──────────────────────────────────────────────
# Helper — Atomic JSON write
# ──────────────────────────────────────────────

def write_json_atomic(filepath: Path, data: dict) -> None:
    """Write JSON file atomically to prevent corruption on crash."""
    tmp_path = filepath.with_suffix('.json.tmp')
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp_path), str(filepath))
    except Exception:
        # Clean up temp file on failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise


# ──────────────────────────────────────────────
# Helper — Strip control characters
# ──────────────────────────────────────────────

def clean_content(text: str) -> str:
    """Strip null bytes and control characters, preserving newlines and tabs."""
    # Remove null bytes and other control chars (keep \n, \t, \r)
    text = text.replace('\x00', '')
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


# ──────────────────────────────────────────────
# 1.1.4 — Base Capture Function
# ──────────────────────────────────────────────

def capture(content: str, capture_type: str, title: str | None = None,
            source_file: str | None = None) -> dict:
    """
    Core capture function. Saves content to raw/ as a JSON file.

    Args:
        content:      The text content to capture
        capture_type: One of "note", "link", "file"
        title:        Optional title (auto-generated if not provided)
        source_file:  Original filename (for file captures)

    Returns:
        The capture data dict

    Raises:
        ValueError: If content is empty or duplicate detected
    """
    # Clean content
    content = clean_content(content)

    # Validate non-empty
    if not content:
        raise ValueError("CAPTURE_EMPTY: Cannot capture empty content. Please provide text.")

    # Generate ID and timestamp
    capture_id = generate_id()
    timestamp = datetime.now(timezone.utc).astimezone().isoformat()

    # Compute hash and check for duplicates
    content_hash = compute_hash(content)
    duplicate_id = check_duplicate(content_hash)
    if duplicate_id:
        raise ValueError(
            f"CAPTURE_DUPLICATE: Duplicate detected — this content matches "
            f"capture '{duplicate_id}'. Skipping."
        )

    # Auto-generate title if not provided
    if not title:
        # Use first 50 chars of content, cleaned up
        title = content[:50].split('\n')[0].strip()
        if len(content) > 50:
            title += "..."

    # Compute word count
    word_count = len(content.split())

    # Build capture data
    data = {
        "id": capture_id,
        "timestamp": timestamp,
        "type": capture_type,
        "title": title,
        "content": content,
        "source_file": source_file,
        "metadata": {
            "word_count": word_count,
            "language": "en",
            "content_hash": content_hash,
        }
    }

    # Determine filename: YYYYMMDD_<hex>.json
    # Extract from ID: cap_YYYYMMDD_hex → YYYYMMDD_hex
    filename_parts = capture_id.split("_", 1)  # ["cap", "YYYYMMDD_hex"]
    filename = f"{filename_parts[1]}.json"
    filepath = config.RAW_DIR / filename

    # Ensure raw/ exists
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Write JSON atomically
    write_json_atomic(filepath, data)

    return data


# ──────────────────────────────────────────────
# 1.2.1 — Capture Note
# ──────────────────────────────────────────────

def capture_note(text: str, title: str | None = None) -> dict:
    """
    Capture a plain text note.

    Args:
        text:  The note content
        title: Optional title

    Returns:
        The capture data dict
    """
    return capture(content=text, capture_type="note", title=title)


# ──────────────────────────────────────────────
# 1.2.2 — Capture Link
# ──────────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    """Check if string is a valid HTTP/HTTPS URL."""
    try:
        result = urlparse(url)
        return result.scheme in ('http', 'https') and bool(result.netloc)
    except Exception:
        return False


def fetch_url_content(url: str) -> tuple[str, str]:
    """
    Fetch a URL and extract readable text + title.

    Returns:
        (extracted_text, page_title)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "SecondSelf/1.0"
        }
        response = requests.get(
            url,
            timeout=config.URL_FETCH_TIMEOUT,
            headers=headers,
            allow_redirects=True,
        )

        # Check if response is binary (PDF, image, etc.)
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return (
                f"[URL: {url}]\n[Content-Type: {content_type}]\n"
                f"Binary content — text extraction not available.",
                url
            )

        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title
        page_title = url
        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Truncate to 2000 chars
        text = text[:2000]

        return text, page_title

    except requests.Timeout:
        return (
            f"[URL: {url}]\nURL request timed out after {config.URL_FETCH_TIMEOUT} seconds.",
            url
        )
    except requests.TooManyRedirects:
        return (
            f"[URL: {url}]\nToo many redirects — could not reach the page.",
            url
        )
    except requests.ConnectionError:
        return (
            f"[URL: {url}]\nCould not connect to the server.",
            url
        )
    except requests.RequestException as e:
        return (
            f"[URL: {url}]\nFetch error: {e}",
            url
        )


def capture_link(url: str, title: str | None = None) -> dict:
    """
    Capture a web link. Fetches the page, extracts text and title.

    Args:
        url:   The URL to capture
        title: Optional override title

    Returns:
        The capture data dict

    Raises:
        ValueError: If URL is invalid
    """
    if not is_valid_url(url):
        raise ValueError(
            f"URL_INVALID: '{url}' is not a valid URL. "
            f"Include http:// or https://"
        )

    # Fetch page content
    extracted_text, page_title = fetch_url_content(url)

    # Build content: URL on first line, then extracted text
    content = f"URL: {url}\n\n{extracted_text}"

    # Use page title if no custom title provided
    if not title:
        title = page_title

    return capture(content=content, capture_type="link", title=title)


# ──────────────────────────────────────────────
# 1.2.3 — Capture File
# ──────────────────────────────────────────────

def extract_pdf_text(filepath: Path) -> str:
    """Extract text from a PDF file using PyPDF2."""
    if PdfReader is None:
        return f"[PDF: {filepath.name}]\nPyPDF2 not installed — cannot extract text."

    try:
        reader = PdfReader(str(filepath))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- Page {i + 1} ---\n{text}")

        full_text = "\n\n".join(pages_text)

        # Check if scanned PDF (very little text extracted)
        if len(full_text.strip()) < 50:
            return (
                f"[PDF: {filepath.name}]\n"
                f"PDF appears to be image-based (scanned). "
                f"Minimal text extracted:\n{full_text}"
            )

        return full_text

    except Exception as e:
        return f"[PDF: {filepath.name}]\nPDF could not be read: {e}"


def capture_file(filepath: str, title: str | None = None) -> dict:
    """
    Capture a local file. Copies to attachments/ and extracts text.

    Supported: .txt, .md, .pdf
    Other formats: saves reference only.

    Args:
        filepath: Path to the file
        title:    Optional title

    Returns:
        The capture data dict

    Raises:
        ValueError: If file doesn't exist or is empty
    """
    path = Path(filepath).resolve()

    # Validate file exists
    if not path.is_file():
        raise ValueError(f"CAPTURE_FILE_NOT_FOUND: File not found: {filepath}")

    # Validate file is not empty
    file_size = path.stat().st_size
    if file_size == 0:
        raise ValueError(f"CAPTURE_FILE_EMPTY: File is empty (0 bytes): {filepath}")

    # Check file size limit
    max_bytes = config.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        print(
            f"⚠️  Warning: File too large ({file_size / (1024*1024):.1f} MB). "
            f"Metadata saved, but content not fully extracted."
        )

    # Generate a temporary ID for the attachment filename
    capture_id = generate_id()
    safe_name = sanitize_filename(path.name)
    attachment_name = f"{capture_id.split('_', 1)[1]}_{safe_name}"

    # Copy file to attachments/
    config.ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = config.ATTACHMENTS_DIR / attachment_name

    if file_size <= max_bytes:
        shutil.copy2(str(path), str(dest_path))

    # Extract content based on file type
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        content = extract_pdf_text(path)
    elif suffix in (".txt", ".md"):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")
    else:
        content = (
            f"[File: {path.name}]\n"
            f"File captured but content extraction not supported for '{suffix}'.\n"
            f"Attachment saved to: {attachment_name}"
        )

    # Default title from filename
    if not title:
        title = path.stem.replace("_", " ").replace("-", " ").title()

    # We already generated an ID above, but capture() generates its own.
    # So we pass the source_file info and let capture() handle the rest.
    # The attachment was already copied with a predictable name.
    return capture(
        content=content,
        capture_type="file",
        title=title,
        source_file=path.name,
    )


# ──────────────────────────────────────────────
# 1.2.4 — Auto-Detection
# ──────────────────────────────────────────────

def capture_auto(input_string: str, title: str | None = None) -> dict:
    """
    Auto-detect input type and route to the correct capture function.

    Detection order:
      1. URL pattern (http:// or https://) → capture_link()
      2. File path (os.path.isfile())      → capture_file()
      3. Everything else                   → capture_note()

    Args:
        input_string: The content to capture
        title:        Optional title

    Returns:
        The capture data dict
    """
    input_stripped = input_string.strip()

    # Check if it's a URL
    if is_valid_url(input_stripped):
        print(f"🔗 Detected as URL → capturing link...")
        return capture_link(input_stripped, title=title)

    # Check if it's a file path
    if os.path.isfile(input_stripped):
        print(f"📄 Detected as file → capturing file...")
        return capture_file(input_stripped, title=title)

    # Default: treat as note
    print(f"📝 Detected as note → capturing note...")
    return capture_note(input_stripped, title=title)


# ──────────────────────────────────────────────
# 1.3.4 — List Captures
# ──────────────────────────────────────────────

def list_captures(filter_type: str | None = None) -> list[dict]:
    """
    List all captures in raw/.

    Args:
        filter_type: Optional filter by type ("note", "link", "file")

    Returns:
        List of capture data dicts, sorted by timestamp (newest first)
    """
    raw_dir = config.RAW_DIR
    captures = []

    if not raw_dir.exists():
        return captures

    for json_file in sorted(raw_dir.glob("*.json"), reverse=True):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if filter_type and data.get("type") != filter_type:
                continue

            captures.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    return captures


def print_captures(captures: list[dict]) -> None:
    """Pretty-print a list of captures to the terminal."""
    if not captures:
        print("📭 No captures found.")
        return

    print(f"\n📚 Found {len(captures)} capture(s):\n")
    print(f"  {'ID':<28} {'Type':<6} {'Words':<6} {'Title'}")
    print(f"  {'─' * 28} {'─' * 6} {'─' * 6} {'─' * 40}")

    for cap in captures:
        cap_id = cap.get("id", "unknown")
        cap_type = cap.get("type", "?")
        word_count = cap.get("metadata", {}).get("word_count", 0)
        title = cap.get("title", "Untitled")

        # Truncate title for display
        if len(title) > 45:
            title = title[:42] + "..."

        # Type emoji
        type_icon = {"note": "📝", "link": "🔗", "file": "📄"}.get(cap_type, "❓")

        print(f"  {cap_id:<28} {type_icon} {cap_type:<4} {word_count:<6} {title}")

    print()


# ──────────────────────────────────────────────
# 1.3 — CLI Interface
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="capture.py",
        description="SecondSelf — Capture anything into your AI Second Brain",
        epilog="Examples:\n"
               "  python capture.py note \"My idea about AI\"\n"
               "  python capture.py link \"https://example.com\"\n"
               "  python capture.py file \"./document.pdf\"\n"
               "  python capture.py auto \"some input\"\n"
               "  python capture.py list --type note",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Capture command")

    # --- note ---
    note_parser = subparsers.add_parser("note", help="Capture a text note")
    note_parser.add_argument("content", type=str, help="The note content")
    note_parser.add_argument("--title", type=str, default=None, help="Optional title")

    # --- link ---
    link_parser = subparsers.add_parser("link", help="Capture a web link")
    link_parser.add_argument("url", type=str, help="The URL to capture")
    link_parser.add_argument("--title", type=str, default=None, help="Optional title")

    # --- file ---
    file_parser = subparsers.add_parser("file", help="Capture a local file")
    file_parser.add_argument("filepath", type=str, help="Path to the file")
    file_parser.add_argument("--title", type=str, default=None, help="Optional title")

    # --- auto ---
    auto_parser = subparsers.add_parser("auto", help="Auto-detect and capture")
    auto_parser.add_argument("input", type=str, help="Text, URL, or file path")
    auto_parser.add_argument("--title", type=str, default=None, help="Optional title")

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List all captures")
    list_parser.add_argument(
        "--type", type=str, choices=["note", "link", "file"],
        default=None, help="Filter by capture type"
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "note":
            result = capture_note(args.content, title=args.title)
            print(f"✅ Captured note: {result['id']}")
            print(f"   Title: {result['title']}")
            print(f"   Words: {result['metadata']['word_count']}")

        elif args.command == "link":
            result = capture_link(args.url, title=args.title)
            print(f"✅ Captured link: {result['id']}")
            print(f"   Title: {result['title']}")
            print(f"   Words: {result['metadata']['word_count']}")

        elif args.command == "file":
            result = capture_file(args.filepath, title=args.title)
            print(f"✅ Captured file: {result['id']}")
            print(f"   Title: {result['title']}")
            print(f"   Source: {result['source_file']}")
            print(f"   Words: {result['metadata']['word_count']}")

        elif args.command == "auto":
            result = capture_auto(args.input, title=args.title)
            print(f"✅ Captured ({result['type']}): {result['id']}")
            print(f"   Title: {result['title']}")
            print(f"   Words: {result['metadata']['word_count']}")

        elif args.command == "list":
            captures = list_captures(filter_type=args.type)
            print_captures(captures)

    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
