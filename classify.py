"""
SecondSelf — Classification Pipeline (Phase 2: The Librarian)

Uses Groq (Llama 3.3) to automatically classify raw captures into PARA categories,
generate a summary, and extract tags. 

Usage:
    python classify.py                  # classify all unprocessed
    python classify.py --file <id>      # classify one specific capture
    python classify.py --rerun          # re-classify everything
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from groq import Groq
import groq

import config


# ──────────────────────────────────────────────
# 2.1 — LLM Integration
# ──────────────────────────────────────────────

def get_llm_client() -> Groq:
    """Initialize Groq client with API key from config."""
    if not config.GROQ_API_KEY or config.GROQ_API_KEY == "gsk_your_key_here":
        print(
            "❌ Error: GROQ_API_KEY not found or invalid.\n"
            "Set it in your .env file.\n"
            "Get your free key at: https://console.groq.com"
        )
        sys.exit(1)
    
    return Groq(api_key=config.GROQ_API_KEY)


def call_llm(client: Groq, system_prompt: str, user_prompt: str) -> dict | None:
    """
    Call Groq API with retries, exponential backoff, and JSON parsing.
    Returns parsed JSON dict, or None if failed.
    """
    retries = config.LLM_RETRY_ATTEMPTS
    delay = config.LLM_RETRY_BASE_DELAY

    for attempt in range(retries):
        try:
            # Respect rate limiting (pause between all calls)
            time.sleep(config.LLM_RATE_LIMIT_DELAY)
            
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
                timeout=30.0
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # EC-2.2.1 Fallback regex parse
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                else:
                    print(f"⚠️  Warning: LLM returned malformed JSON on attempt {attempt+1}")
                    raise ValueError("Malformed JSON")
                    
        except (groq.RateLimitError, groq.APIConnectionError, groq.InternalServerError) as e:
            print(f"⚠️  API Error: {e}. Retrying in {delay}s... ({attempt+1}/{retries})")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
        except groq.AuthenticationError:
            print("❌ Error: Invalid GROQ_API_KEY. Please check your key at https://console.groq.com")
            sys.exit(1)
        except Exception as e:
            print(f"⚠️  Unexpected LLM Error: {e}")
            time.sleep(delay)
            delay *= 2
            
    print("❌ Failed to get valid response from LLM after all retries.")
    return None


# ──────────────────────────────────────────────
# 2.2 — Classification Engine
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are a knowledge organizer using the PARA method.
Categories:
- projects: Active, time-bound goals
- areas: Ongoing responsibilities
- resources: Reference material for future use
- archives: Inactive/completed items

Respond ONLY in this JSON format. Do not include any other text:
{
  "category": "projects|areas|resources|archives",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "One-line summary of the content",
  "suggested_title": "A clear, descriptive title"
}"""

def sanitize_category(category: str) -> str:
    """Fuzzy match category to ensure it fits PARA."""
    cat = str(category).lower()
    if any(x in cat for x in ["proj"]): return "projects"
    if any(x in cat for x in ["area", "resp"]): return "areas"
    if any(x in cat for x in ["res", "ref"]): return "resources"
    if any(x in cat for x in ["arch", "old"]): return "archives"
    return "archives"  # Safe default (EC-2.2.2)


def classify_note(client: Groq, raw_capture: dict, force_rerun: bool = False) -> bool:
    """
    Classify a single note and move it to the wiki/ directory.
    Returns True if processed successfully, False otherwise.
    """
    capture_id = raw_capture.get("id")
    if not capture_id:
        return False
        
    # Check if already classified
    if not force_rerun:
        for category in config.PARA_CATEGORIES:
            target_path = config.WIKI_DIR / category / f"{capture_id}.json"
            if target_path.exists():
                return True  # Already processed

    print(f"🧠 Classifying {capture_id}...")
    
    # Cap content length to prevent token overflow (EC-1.1.2)
    content = raw_capture.get("content", "")
    content = content[:config.MAX_RAW_CONTENT]
    
    user_prompt = f"Classify this content:\n---\n{content}\n---"
    
    # Call LLM
    result = call_llm(client, SYSTEM_PROMPT, user_prompt)
    
    # Handle classification failure
    if not result:
        print(f"   ❌ Failed to classify {capture_id}")
        return False
        
    # Extract and clean fields
    category = sanitize_category(result.get("category", "archives"))
    tags = result.get("tags", [])
    if not isinstance(tags, list): tags = []
    
    summary = result.get("summary", "")
    # Truncate overly long summaries (EC-2.2.4)
    if len(summary) > 150:
        summary = summary[:150].rsplit(' ', 1)[0] + '...'
        
    suggested_title = result.get("suggested_title", raw_capture.get("title", ""))
    
    # Build enriched note structure
    enriched_note = {
        "id": capture_id,
        "original_id": capture_id,
        "timestamp": raw_capture.get("timestamp"),
        "classified_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "type": raw_capture.get("type"),
        "title": raw_capture.get("title") or suggested_title,
        "content": raw_capture.get("content"),
        "para_category": category,
        "tags": tags,
        "summary": summary,
        "links": [],  # Will be populated by link.py
        "embedding": None  # Will be populated by link.py
    }
    
    # Carry over original metadata but preserve source file
    if "source_file" in raw_capture:
        enriched_note["source_file"] = raw_capture["source_file"]
        
    # Ensure wiki category dir exists
    cat_dir = config.WIKI_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    # Atomic save to wiki/
    target_path = cat_dir / f"{capture_id}.json"
    tmp_path = target_path.with_suffix('.json.tmp')
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(enriched_note, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp_path), str(target_path))
        print(f"   ✅ Saved to wiki/{category}/")
        return True
    except Exception as e:
        if tmp_path.exists(): tmp_path.unlink()
        print(f"   ❌ File write error: {e}")
        return False


def classify_all(force_rerun: bool = False):
    """Scan raw/ and classify all unprocessed files."""
    raw_dir = config.RAW_DIR
    if not raw_dir.exists():
        print("📭 No raw captures found.")
        return
        
    client = get_llm_client()
    files = list(raw_dir.glob("*.json"))
    
    if not files:
        print("📭 No raw captures found.")
        return
        
    print(f"🔍 Found {len(files)} total captures in raw/.")
    processed = 0
    skipped = 0
    
    for idx, filepath in enumerate(files, 1):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_capture = json.load(f)
                
            # Check if it already exists (skip LLM call if so)
            capture_id = raw_capture.get("id", filepath.stem)
            already_classified = False
            if not force_rerun:
                for category in config.PARA_CATEGORIES:
                    if (config.WIKI_DIR / category / f"{capture_id}.json").exists():
                        already_classified = True
                        break
            
            if already_classified:
                skipped += 1
                continue
                
            print(f"\n[{idx}/{len(files)}]")
            success = classify_note(client, raw_capture, force_rerun)
            if success:
                processed += 1
                
        except (json.JSONDecodeError, OSError):
            print(f"⚠️  Skipping unreadable file: {filepath.name}")
            continue
            
    print(f"\n✨ Classification complete: {processed} processed, {skipped} skipped.")


def classify_single(capture_id: str, force_rerun: bool = False):
    """Classify one specific capture."""
    client = get_llm_client()
    
    # Find it in raw/
    for filepath in config.RAW_DIR.glob("*.json"):
        if capture_id in filepath.name:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_capture = json.load(f)
                classify_note(client, raw_capture, force_rerun)
                return
            except Exception as e:
                print(f"❌ Error reading file: {e}")
                return
                
    print(f"❌ Capture ID '{capture_id}' not found in raw/.")


# ──────────────────────────────────────────────
# CLI Interface
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SecondSelf — Auto-Classify Notes (The Librarian)"
    )
    parser.add_argument("--file", type=str, help="Classify a specific capture ID")
    parser.add_argument("--rerun", action="store_true", help="Re-classify all files")
    
    args = parser.parse_args()
    
    if args.file:
        classify_single(args.file, force_rerun=args.rerun)
    else:
        classify_all(force_rerun=args.rerun)


if __name__ == "__main__":
    main()
