"""
SecondSelf — Obsidian Vault Exporter

Converts the entire structured JSON knowledge base (wiki/) into an 
Obsidian-compatible Markdown vault, complete with YAML frontmatter, tags, 
and automated [[Wikilinks]] to power the native Obsidian Graph View!

Usage:
    python export_to_obsidian.py
    python export_to_obsidian.py --output "./my_obsidian_vault"
"""

import argparse
import json
import os
import re
from pathlib import Path

import config


def sanitize_filename(name: str) -> str:
    """Strip invalid characters from note titles to make them safe Windows/macOS filenames."""
    # Replace slashes and illegal filesystem characters with hyphens or spaces
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    # Remove trailing/leading periods or spaces
    clean = clean.strip().strip(".")
    # Fallback if empty
    if not clean:
        clean = "Untitled Note"
    return clean[:100] # Cap length to prevent filesystem errors


def export_vault(output_dir: Path):
    """Convert all JSON notes in wiki/ into Markdown files with wikilinks in output_dir."""
    if not config.WIKI_DIR.exists():
        print("❌ No wiki/ directory found! Capture and process some notes first.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create standard PARA folders inside the Obsidian Vault
    for category in config.PARA_CATEGORIES:
        (output_dir / category).mkdir(exist_ok=True)
        
    notes = []
    # First pass: Load all notes and build a mapping from ID -> safe Markdown Title
    id_to_title = {}
    
    for json_file in config.WIKI_DIR.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            note_id = data.get("id")
            raw_title = data.get("title", "Untitled Note")
            safe_title = sanitize_filename(raw_title)
            
            # Ensure unique titles if duplicates occur
            original_safe = safe_title
            counter = 2
            while safe_title in id_to_title.values() and id_to_title.get(note_id) != safe_title:
                safe_title = f"{original_safe} ({counter})"
                counter += 1
                
            if note_id:
                id_to_title[note_id] = safe_title
                notes.append((data, safe_title))
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Skipping invalid file {json_file.name}: {e}")
            continue

    if not notes:
        print("📭 No notes found in wiki/. Your knowledge base is empty.")
        return

    print(f"📦 Exporting {len(notes)} notes to Obsidian Vault at: '{output_dir}'...")
    
    exported_count = 0
    total_wikilinks = 0
    
    # Second pass: Generate the Markdown files with frontmatter and wikilinks
    for data, safe_title in notes:
        category = data.get("para_category", "archives").lower()
        if category not in config.PARA_CATEGORIES:
            category = "archives"
            
        target_path = output_dir / category / f"{safe_title}.md"
        
        # Build YAML Frontmatter for Obsidian properties
        tags = data.get("tags", [])
        timestamp = data.get("timestamp", "")
        note_type = data.get("type", "note")
        word_count = data.get("word_count", 0)
        
        lines = []
        lines.append("---")
        lines.append(f"title: \"{data.get('title', safe_title)}\"")
        lines.append(f"id: {data.get('id', 'unknown')}")
        lines.append(f"type: {note_type}")
        lines.append(f"category: {category}")
        if timestamp:
            lines.append(f"created: \"{timestamp}\"")
        if word_count:
            lines.append(f"word_count: {word_count}")
        if tags and isinstance(tags, list):
            lines.append("tags:")
            for t in tags:
                clean_tag = str(t).replace(" ", "-").replace("#", "")
                lines.append(f"  - {clean_tag}")
        lines.append("---")
        lines.append("")
        
        # Title Header
        lines.append(f"# {data.get('title', safe_title)}")
        lines.append("")
        
        # Summary Blockquote
        summary = data.get("summary")
        if summary:
            lines.append(f"> [!ABSTRACT] Summary")
            lines.append(f"> {summary}")
            lines.append("")
            
        # Main Content
        content = data.get("content", "").strip()
        if content:
            lines.append("## Content")
            lines.append(content)
            lines.append("")
            
        # Semantic Wikilinks (The magic for Obsidian Graph View)
        links = data.get("links", [])
        if links and isinstance(links, list):
            lines.append("---")
            lines.append("## 🔗 Connected Thoughts")
            lines.append("")
            
            for link in links:
                target_id = link.get("target_id")
                similarity = link.get("similarity", 0.0)
                
                # Resolve ID to safe Markdown title
                target_title = id_to_title.get(target_id)
                if target_title:
                    lines.append(f"- [[{target_title}]] *(similarity: {similarity:.2f})*")
                    total_wikilinks += 1
                elif link.get("target_title"):
                    # Fallback to recorded target title if ID not found
                    clean_target = sanitize_filename(link["target_title"])
                    lines.append(f"- [[{clean_target}]] *(similarity: {similarity:.2f})*")
                    total_wikilinks += 1

        # Write out file
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            exported_count += 1
        except Exception as e:
            print(f"❌ Error writing {target_path.name}: {e}")

    print(f"✨ Success! Exported {exported_count} Markdown notes containing {total_wikilinks} Obsidian [[Wikilinks]].")
    print(f"\n👉 How to view in Obsidian:")
    print(f"   1. Open Obsidian and click 'Open another vault' -> 'Open folder as vault'.")
    print(f"   2. Select the folder: {output_dir.resolve()}")
    print(f"   3. Click 'Open graph view' in Obsidian's left toolbar!")


def main():
    parser = argparse.ArgumentParser(description="Export SecondSelf knowledge base to an Obsidian Vault.")
    parser.add_argument(
        "--output", 
        "-o", 
        type=Path, 
        default=Path("obsidian_vault"), 
        help="Path where the Obsidian Markdown folder should be created"
    )
    args = parser.parse_args()
    
    export_vault(args.output)


if __name__ == "__main__":
    main()
