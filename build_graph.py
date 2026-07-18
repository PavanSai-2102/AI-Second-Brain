"""
SecondSelf — Graph Data Builder (Phase 3: The Cartographer)

Scans the classified, linked notes in the wiki/ directory and generates
a graph.json file containing the nodes and edges for visualization.

Usage:
    python build_graph.py                # build graph.json
    python build_graph.py --stats        # print graph statistics
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import config


# ──────────────────────────────────────────────
# 3.1.1 — Load Notes
# ──────────────────────────────────────────────

def load_all_notes() -> list[dict]:
    """Recursively scan wiki/ subdirectories and load all notes."""
    notes = []
    if not config.WIKI_DIR.exists():
        return notes
        
    for json_file in config.WIKI_DIR.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Check for required fields (EC-3.1.4)
                if not data.get("id"):
                    continue
                    
                # Provide defaults for missing fields
                data.setdefault("title", "Untitled Note")
                data.setdefault("para_category", "archives")
                data.setdefault("tags", [])
                data.setdefault("summary", data.get("content", "")[:100])
                data.setdefault("content", "")
                data.setdefault("links", [])
                
                notes.append(data)
        except (json.JSONDecodeError, OSError):
            print(f"⚠️  Warning: Failed to read {json_file.name}")
            continue
            
    return notes


# ──────────────────────────────────────────────
# 3.1.2 — Build Nodes
# ──────────────────────────────────────────────

def build_nodes(notes: list[dict]) -> list[dict]:
    """Convert note objects into graph node objects."""
    nodes = []
    
    for note in notes:
        # Extract metadata
        note_id = note["id"]
        title = note["title"]
        category = note["para_category"]
        tags = note["tags"]
        summary = note["summary"]
        
        # Truncate label to 25 chars
        label = title
        if len(label) > 25:
            label = label[:22] + "..."
            
        # Extract content preview
        content = note["content"]
        content_preview = content[:200]
        if len(content) > 200:
            content_preview += "..."
            
        link_count = len(note["links"])
        created = note.get("timestamp", "")
        
        node = {
            "id": note_id,
            "label": label,
            "full_title": title,
            "category": category,
            "tags": tags,
            "summary": summary,
            "content_preview": content_preview,
            "created": created,
            "link_count": link_count
        }
        nodes.append(node)
        
    return nodes


# ──────────────────────────────────────────────
# 3.1.3 — Build Edges
# ──────────────────────────────────────────────

def build_edges(notes: list[dict]) -> list[dict]:
    """Extract links from notes and build deduplicated edge objects."""
    edges = []
    seen_edges = set()
    
    # Track existing node IDs to prevent dangling links (EC-2.4.4)
    existing_node_ids = {note["id"] for note in notes}
    
    for note in notes:
        source_id = note["id"]
        
        for link in note["links"]:
            target_id = link.get("target_id")
            
            # Skip invalid or dangling links
            if not target_id or target_id not in existing_node_ids:
                continue
                
            similarity = link.get("similarity", 0.0)
            
            # Create a sorted tuple of (source, target) to deduplicate bidirectional links
            edge_key = tuple(sorted([source_id, target_id]))
            
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    "source": source_id,
                    "target": target_id,
                    "similarity": similarity
                })
                
    return edges


# ──────────────────────────────────────────────
# 3.1.4 — Build Graph
# ──────────────────────────────────────────────

def build_graph(print_stats_only: bool = False):
    """Load notes, build nodes/edges, and write to graph.json."""
    print("🗺️  Building knowledge graph...")
    
    notes = load_all_notes()
    
    if not notes:
        print("📭 No classified notes found in wiki/. Cannot build graph.")
        # Produce valid but empty graph (EC-3.1.1)
        nodes = []
        edges = []
    else:
        nodes = build_nodes(notes)
        edges = build_edges(notes)
        
    # Aggregate some stats
    categories = {}
    for node in nodes:
        cat = node["category"]
        categories[cat] = categories.get(cat, 0) + 1
        
    if print_stats_only:
        print("\n📊 Graph Statistics:")
        print("───────────────────────────")
        print(f"Total Nodes: {len(nodes)}")
        print(f"Total Edges: {len(edges)}")
        print("\nBreakdown by Category:")
        for cat in config.PARA_CATEGORIES:
            count = categories.get(cat, 0)
            print(f"  {cat.capitalize():<10} {count}")
        return
        
    # Assemble final JSON
    graph_data = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        },
        "nodes": nodes,
        "edges": edges
    }
    
    # Save to graph.json
    try:
        with open(config.GRAPH_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        print(f"✨ Successfully generated {config.GRAPH_JSON_PATH.name}")
        print(f"   Nodes: {len(nodes)} | Edges: {len(edges)}")
    except Exception as e:
        print(f"❌ Error writing graph.json: {e}")
        sys.exit(1)


# ──────────────────────────────────────────────
# 3.1.5 — CLI Interface
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SecondSelf — Graph Data Builder (The Cartographer)"
    )
    parser.add_argument(
        "--stats", 
        action="store_true", 
        help="Print graph statistics without generating graph.json"
    )
    
    args = parser.parse_args()
    build_graph(print_stats_only=args.stats)


if __name__ == "__main__":
    main()
