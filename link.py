"""
SecondSelf — Semantic Linking Pipeline (Phase 2: The Librarian)

Uses sentence-transformers to generate embeddings for all classified notes,
then computes cosine similarity to automatically link related notes.

Usage:
    python link.py                     # full pipeline: embed + link
    python link.py embed               # compute embeddings for all
    python link.py link                # just linking
    python link.py link --threshold 0.7  # custom threshold
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import warnings

# Suppress HuggingFace warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

import config


# ──────────────────────────────────────────────
# Global Model Cache
# ──────────────────────────────────────────────
_model = None

def get_model():
    """Lazy load the embedding model to save memory if only linking."""
    global _model
    if _model is None:
        if SentenceTransformer is None:
            print("❌ Error: sentence-transformers not installed.")
            sys.exit(1)
        print(f"🔄 Loading embedding model ({config.EMBEDDING_MODEL})...")
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


# ──────────────────────────────────────────────
# 2.3 — Embedding Computation
# ──────────────────────────────────────────────

def load_all_wiki_notes() -> list[tuple[Path, dict]]:
    """Recursively load all JSON notes from wiki/ directory."""
    notes = []
    if not config.WIKI_DIR.exists():
        return notes
        
    for json_file in config.WIKI_DIR.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                notes.append((json_file, data))
        except (json.JSONDecodeError, OSError):
            continue
            
    return notes


def compute_embedding(note_data: dict) -> list[float] | None:
    """Combine title, summary, and content to compute 384-dim embedding."""
    title = note_data.get("title", "")
    summary = note_data.get("summary", "")
    content = note_data.get("content", "")
    
    # Empty notes get None embedding (EC-2.3.1)
    if not (title or summary or content):
        return None
        
    # Cap content to prevent huge inputs (EC-2.3.2)
    text_to_embed = f"{title} {summary} {content[:500]}"
    
    model = get_model()
    # encode() returns a numpy array, we need a standard Python list of floats for JSON
    embedding = model.encode(text_to_embed).tolist()
    return embedding


def embed_all_notes(force_rerun: bool = False):
    """Scan wiki/ and compute embeddings for any note missing one."""
    notes = load_all_wiki_notes()
    if not notes:
        print("📭 No classified notes found in wiki/.")
        return
        
    processed = 0
    skipped = 0
    
    for filepath, note_data in notes:
        # Check if embedding already exists
        if note_data.get("embedding") and not force_rerun:
            skipped += 1
            continue
            
        print(f"🧮 Embedding {note_data.get('id', filepath.name)}...")
        
        embedding = compute_embedding(note_data)
        if embedding:
            # Update data
            note_data["embedding"] = embedding
            
            # Atomic save back to the same file
            tmp_path = filepath.with_suffix('.json.tmp')
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(note_data, f, indent=2, ensure_ascii=False)
                os.replace(str(tmp_path), str(filepath))
                processed += 1
            except Exception as e:
                if tmp_path.exists(): tmp_path.unlink()
                print(f"   ❌ File write error: {e}")
        else:
            print(f"   ⚠️  Skipped (empty content)")
            
    print(f"✨ Embedding complete: {processed} generated, {skipped} already existed.")


# ──────────────────────────────────────────────
# 2.4 — Auto-Linking Related Notes
# ──────────────────────────────────────────────

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    
    # Handle NaN or zero vectors (EC-5.2.4)
    if np.any(np.isnan(a)) or np.any(np.isnan(b)):
        return 0.0
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(np.dot(a, b) / (norm_a * norm_b))


def link_all(threshold: float | None = None):
    """Compute NxN similarities and build links between notes."""
    if threshold is None:
        threshold = config.SIMILARITY_THRESHOLD
        
    # Validate threshold range
    if not (0.3 <= threshold <= 0.95):
        print(f"⚠️  Warning: Threshold {threshold} out of bounds, clamped to 0.65")
        threshold = 0.65

    notes = load_all_wiki_notes()
    if len(notes) < 2:
        print("📭 Need at least 2 notes in wiki/ to find connections (EC-2.4.1).")
        return
        
    # Extract only notes with valid embeddings
    valid_notes = []
    for filepath, data in notes:
        emb = data.get("embedding")
        if emb and len(emb) == config.EMBEDDING_DIMENSION:
            valid_notes.append({"path": filepath, "data": data, "emb": emb})
            
    if len(valid_notes) < 2:
        print("📭 Not enough notes have embeddings. Run 'python link.py embed' first.")
        return
        
    print(f"🔗 Finding connections between {len(valid_notes)} notes (threshold > {threshold})...")
    
    # Build a dictionary to hold the new links for each note
    # Structure: { note_id: { target_id: link_dict } }
    new_links_map = {n["data"]["id"]: {} for n in valid_notes}
    
    total_links_found = 0
    now_iso = datetime.now(timezone.utc).astimezone().isoformat()
    
    # NxN comparison (O(N^2) but fine for < 1000 notes)
    for i in range(len(valid_notes)):
        node_a = valid_notes[i]
        id_a = node_a["data"]["id"]
        
        for j in range(i + 1, len(valid_notes)):
            node_b = valid_notes[j]
            id_b = node_b["data"]["id"]
            
            sim = cosine_similarity(node_a["emb"], node_b["emb"])
            
            if sim > threshold:
                total_links_found += 1
                
                # A -> B
                new_links_map[id_a][id_b] = {
                    "target_id": id_b,
                    "target_title": node_b["data"]["title"],
                    "similarity": round(sim, 3),
                    "linked_at": now_iso
                }
                
                # B -> A
                new_links_map[id_b][id_a] = {
                    "target_id": id_a,
                    "target_title": node_a["data"]["title"],
                    "similarity": round(sim, 3),
                    "linked_at": now_iso
                }
                
    if total_links_found == 0:
        print("💡 No links found. Try lowering the threshold in config.py or --threshold arg.")
        return
        
    # Now merge new links with existing links and save
    saved_count = 0
    for node in valid_notes:
        id_a = node["data"]["id"]
        new_links_for_a = new_links_map[id_a]
        
        if not new_links_for_a:
            continue
            
        # Get existing links (convert to dict keyed by target_id for easy merging/deduping)
        current_links = node["data"].get("links", [])
        if not isinstance(current_links, list):
            current_links = []
            
        merged_links = {link["target_id"]: link for link in current_links if "target_id" in link}
        
        # Merge new links (updates similarity score and linked_at if already exists)
        for target_id, new_link in new_links_for_a.items():
            merged_links[target_id] = new_link
            
        # Save back to list
        node["data"]["links"] = list(merged_links.values())
        
        # Atomic save
        filepath = node["path"]
        tmp_path = filepath.with_suffix('.json.tmp')
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(node["data"], f, indent=2, ensure_ascii=False)
            os.replace(str(tmp_path), str(filepath))
            saved_count += 1
        except Exception as e:
            if tmp_path.exists(): tmp_path.unlink()
            print(f"   ❌ File write error: {e}")
            
    print(f"✨ Found {total_links_found} connections (bidirectional pairs). Updated {saved_count} notes.")


# ──────────────────────────────────────────────
# CLI Interface
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SecondSelf — Auto-Link Notes via Embeddings (The Librarian)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # embed command
    embed_parser = subparsers.add_parser("embed", help="Compute embeddings only")
    embed_parser.add_argument("--force", action="store_true", help="Re-embed all notes")
    
    # link command
    link_parser = subparsers.add_parser("link", help="Compute links only")
    link_parser.add_argument("--threshold", type=float, help="Override similarity threshold")
    
    args = parser.parse_args()
    
    if args.command == "embed":
        embed_all_notes(force_rerun=args.force)
    elif args.command == "link":
        link_all(threshold=args.threshold)
    else:
        # Default behavior: run both
        print("🚀 Running full semantic pipeline (Embed -> Link)")
        embed_all_notes(force_rerun=False)
        link_all(threshold=None)


if __name__ == "__main__":
    main()
