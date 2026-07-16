# SecondSelf — Phase-Wise Implementation Plan

A step-by-step build guide for the AI Second Brain project, broken into 4 phases (one per week). Each phase builds on the previous — no phase can be skipped.

---

## Project Timeline Overview

```
  Week 1                Week 2                Week 3                Week 4
  ┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
  │   THE    │          │   THE    │          │   THE    │          │   THE    │
  │ ARCHIVIST│────────► │ LIBRARIAN│────────► │CARTOGRAPH│────────► │  ORACLE  │
  │          │          │          │          │          │          │          │
  │ Capture  │          │ Classify │          │ Visualize│          │ Ask + UI │
  │ Pipeline │          │ + Link   │          │ Graph    │          │ + Deploy │
  └──────────┘          └──────────┘          └──────────┘          └──────────┘
       │                     │                     │                     │
       ▼                     ▼                     ▼                     ▼
   raw/ folder          wiki/ folder          graph.json           Public URL
   10+ captures         15+ classified        Interactive          Live app
                        + auto-linked         brain graph          with RAG
```

---

## Pre-Setup (Day 0) — Project Scaffolding

**Goal:** Set up the repository, virtual environment, and folder structure.

### Tasks

- [ ] **P0.1** Create the project root directory

```bash
mkdir secondself && cd secondself
```

- [ ] **P0.2** Initialize Git repository

```bash
git init
```

- [ ] **P0.3** Create the directory structure

```bash
mkdir -p raw/attachments wiki/projects wiki/areas wiki/resources wiki/archives
```

```
secondself/
├── raw/
│   └── attachments/
├── wiki/
│   ├── projects/
│   ├── areas/
│   ├── resources/
│   └── archives/
```

- [ ] **P0.4** Set up Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

- [ ] **P0.5** Create `requirements.txt`

```
streamlit>=1.30.0
groq>=0.4.0
sentence-transformers>=2.2.0
numpy>=1.24.0
requests>=2.31.0
beautifulsoup4>=4.12.0
PyPDF2>=3.0.0
python-dotenv>=1.0.0
```

```bash
pip install -r requirements.txt
```

- [ ] **P0.6** Create `.env` file (add to `.gitignore`)

```
GROQ_API_KEY=gsk_your_key_here
SIMILARITY_THRESHOLD=0.65
```

- [ ] **P0.7** Create `.gitignore`

```
venv/
.env
__pycache__/
*.pyc
.DS_Store
```

- [ ] **P0.8** Create `config.py` — centralized configuration

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Directories
RAW_DIR = "raw"
WIKI_DIR = "wiki"
ATTACHMENTS_DIR = "raw/attachments"

# PARA Categories
PARA_CATEGORIES = ["projects", "areas", "resources", "archives"]

# Embedding Settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.65))

# RAG Settings
TOP_K = 5
MAX_CONTENT_LENGTH = 1500
```

### Verification

```bash
python -c "from config import *; print('Config loaded OK')"
```

### Deliverable

- [ ] Clean repo with folder structure, virtual environment, and config ready

---

---

## Phase 1 — The Archivist: Capture Pipeline (Week 1)

**🏅 Badge: The Archivist**
**Goal:** Build a single command that captures any note, link, or file into `raw/` with a timestamp and unique ID.

---

### Phase 1.1 — Core Capture Function

**File:** `capture.py`
**Estimated Time:** 2-3 hours

#### Tasks

- [ ] **1.1.1** Create the `generate_id()` function
  - Format: `cap_YYYYMMDD_<8-char-hex>`
  - Use `uuid.uuid4().hex[:8]` for uniqueness

- [ ] **1.1.2** Create the `compute_hash(content)` function
  - SHA-256 hash of content string
  - Used for duplicate detection

- [ ] **1.1.3** Create the `check_duplicate(content_hash)` function
  - Scan all existing JSON files in `raw/`
  - Compare `metadata.content_hash`
  - Return `True` if duplicate found

- [ ] **1.1.4** Create the base `capture(content, type, title)` function
  - Generate ID + timestamp
  - Compute content hash
  - Check for duplicates
  - Build JSON structure:

```json
{
  "id": "cap_20260716_a3f8b2c1",
  "timestamp": "2026-07-16T20:30:00+05:30",
  "type": "note",
  "title": "User-provided or auto-generated",
  "content": "The raw text content",
  "source_file": null,
  "metadata": {
    "word_count": 42,
    "language": "en",
    "content_hash": "sha256:abc123..."
  }
}
```

  - Write to `raw/<date>_<hex>.json`

#### Data Model

```
  ┌──────────────────────────────────────────────┐
  │              Raw Capture JSON                 │
  │                                               │
  │  id ──────────── "cap_20260716_a3f8b2c1"      │
  │  timestamp ───── ISO 8601 with timezone       │
  │  type ────────── "note" | "link" | "file"     │
  │  title ───────── String                       │
  │  content ─────── Raw text / URL / extracted   │
  │  source_file ─── Original filename (if file)  │
  │  metadata ────┐                               │
  │               ├── word_count: Integer          │
  │               ├── language: "en"               │
  │               └── content_hash: "sha256:..."   │
  └──────────────────────────────────────────────┘
```

---

### Phase 1.2 — Content Type Handlers

**File:** `capture.py` (continued)
**Estimated Time:** 2-3 hours

#### Tasks

- [ ] **1.2.1** Implement `capture_note(text, title=None)`
  - Accept plain text
  - Auto-generate title from first 50 chars if not provided
  - Set `type = "note"`

- [ ] **1.2.2** Implement `capture_link(url, title=None)`
  - Validate URL format (regex or `urllib.parse`)
  - Fetch page content using `requests`
  - Extract title from `<title>` tag using `BeautifulSoup`
  - Strip HTML, extract readable text (first 2000 chars)
  - Set `type = "link"`
  - Store both URL and extracted text in `content`

- [ ] **1.2.3** Implement `capture_file(filepath, title=None)`
  - Validate file exists
  - Copy original file to `raw/attachments/<id>_<filename>`
  - If PDF: extract text using `PyPDF2`
  - If `.txt` / `.md`: read content directly
  - Set `type = "file"`, set `source_file` field

- [ ] **1.2.4** Implement auto-detection in `capture_auto(input_string)`
  - URL pattern → call `capture_link()`
  - File path exists → call `capture_file()`
  - Otherwise → call `capture_note()`

#### Flow

```
  User Input
      │
      ▼
  ┌─────────────┐     ┌───────────────────────────┐
  │ Auto-Detect │────►│ Is it a URL?              │──YES──► capture_link()
  │             │     │ (http:// or https://)     │
  └─────────────┘     └───────────┬───────────────┘
                                  │ NO
                                  ▼
                      ┌───────────────────────────┐
                      │ Is it a file path?        │──YES──► capture_file()
                      │ (os.path.isfile())        │
                      └───────────┬───────────────┘
                                  │ NO
                                  ▼
                            capture_note()
```

---

### Phase 1.3 — CLI Interface

**File:** `capture.py` (add `if __name__ == "__main__"` block)
**Estimated Time:** 1 hour

#### Tasks

- [ ] **1.3.1** Set up `argparse` with subcommands

```bash
# Usage examples:
python capture.py note "My brilliant idea about AI agents"
python capture.py link "https://arxiv.org/abs/2301.00001"
python capture.py file "./documents/research.pdf"
python capture.py auto "https://example.com"   # auto-detect
```

- [ ] **1.3.2** Add `--title` optional flag for all subcommands
- [ ] **1.3.3** Add success/error output messages with colors (optional)
- [ ] **1.3.4** Add `list` subcommand to show all captures

```bash
python capture.py list                    # show all
python capture.py list --type note        # filter by type
```

---

### Phase 1.4 — Testing with Real Data

**Estimated Time:** 1-2 hours

#### Tasks

- [ ] **1.4.1** Capture 3+ real **notes** (ideas, thoughts, learnings)
- [ ] **1.4.2** Capture 3+ real **links** (articles, docs, blog posts)
- [ ] **1.4.3** Capture 3+ real **files** (PDFs, text files, markdown)
- [ ] **1.4.4** Test duplicate detection — capture the same note twice
- [ ] **1.4.5** Verify all JSON files are well-formed
- [ ] **1.4.6** Verify `raw/` has 10+ items

### Phase 1 — Acceptance Criteria

```
  ┌───────────────────────────────────────────────────────┐
  │  ✅ Phase 1 Complete When:                            │
  │                                                       │
  │  [ ] raw/ and wiki/ folder structure exists            │
  │  [ ] One command captures a note, a link, AND a file  │
  │  [ ] Every capture has a timestamp + unique ID        │
  │  [ ] Duplicate detection works                        │
  │  [ ] 10+ real items captured (not test data)          │
  │  [ ] All JSON files valid and consistent              │
  │                                                       │
  │  🏅 Badge Earned: The Archivist                       │
  └───────────────────────────────────────────────────────┘
```

---

---

## Phase 2 — The Librarian: Auto-Classify + Auto-Link (Week 2)

**🏅 Badge: The Librarian**
**Goal:** AI automatically classifies every capture into PARA categories, adds tags + summaries, and discovers relationships between notes.

---

### Phase 2.1 — LLM Integration Setup

**File:** `classify.py`
**Estimated Time:** 1-2 hours
**Dependency:** Phase 1 complete, `GROQ_API_KEY` in `.env`

#### Tasks

- [ ] **2.1.1** Create `get_llm_client()` function
  - Initialize Groq client with API key from config
  - Handle missing API key gracefully

- [ ] **2.1.2** Create `call_llm(prompt, system_prompt)` function
  - Send request to Groq (Llama 3.3 70B)
  - Parse JSON response
  - Implement retry logic (3 retries, exponential backoff: 2s, 4s, 8s)
  - Implement rate limiting (`time.sleep(2)` between calls)
  - Handle errors: timeout, rate limit, malformed response

- [ ] **2.1.3** Test LLM connection with a simple classification

---

### Phase 2.2 — PARA Classification Engine

**File:** `classify.py` (continued)
**Estimated Time:** 3-4 hours

#### Tasks

- [ ] **2.2.1** Create the classification prompt template

```
SYSTEM: You are a knowledge organizer using the PARA method.
Categories:
- projects: Active, time-bound goals
- areas: Ongoing responsibilities
- resources: Reference material for future use
- archives: Inactive/completed items

USER: Classify this content:
---
{content}
---
Respond ONLY in this JSON format:
{
  "category": "projects|areas|resources|archives",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "One-line summary of the content",
  "suggested_title": "A clear, descriptive title"
}
```

- [ ] **2.2.2** Create `classify_note(raw_capture)` function
  - Load raw JSON from `raw/`
  - Build prompt with content
  - Call LLM
  - Parse response JSON
  - Build enriched note structure:

```json
{
  "id": "cap_20260716_a3f8b2c1",
  "original_id": "cap_20260716_a3f8b2c1",
  "timestamp": "2026-07-16T20:30:00+05:30",
  "classified_at": "2026-07-16T20:31:00+05:30",
  "type": "note",
  "title": "Understanding Vector Embeddings",
  "content": "The raw text content...",
  "para_category": "resources",
  "tags": ["machine-learning", "embeddings", "nlp"],
  "summary": "Overview of how vector embeddings...",
  "links": [],
  "embedding": null
}
```

  - Save to `wiki/<para_category>/<id>.json`

- [ ] **2.2.3** Create `classify_all()` function
  - Scan all files in `raw/`
  - Check if already classified (exists in `wiki/`)
  - Classify unprocessed files
  - Print progress: `[3/15] Classifying: cap_20260716_a3f8b2c1...`

- [ ] **2.2.4** Add CLI entry point

```bash
python classify.py                  # classify all unprocessed
python classify.py --file <id>      # classify one specific capture
python classify.py --rerun          # re-classify everything
```

#### Classification Flow

```
  raw/*.json                         wiki/
      │                                │
      ▼                                │
  ┌──────────┐     ┌──────────┐        │
  │ Load raw │────►│  Build   │        │
  │ capture  │     │  prompt  │        │
  └──────────┘     └────┬─────┘        │
                        │              │
                        ▼              │
                   ┌─────────┐         │
                   │ Groq    │         │
                   │ LLM API │         │
                   └────┬────┘         │
                        │              │
                        ▼              │
                   ┌─────────┐         │
                   │ Parse   │         │
                   │ JSON    │         │
                   └────┬────┘         │
                        │              │
                        ▼              │
                   ┌──────────────┐    │
                   │ Enriched     │    │
                   │ note with    │    │
                   │ category +   │    │
                   │ tags +       │    │
                   │ summary      │    │
                   └──────┬───────┘    │
                          │            │
                          ▼            ▼
                    wiki/resources/cap_xxx.json
                    wiki/projects/cap_yyy.json
                    wiki/areas/cap_zzz.json
```

---

### Phase 2.3 — Embedding Computation

**File:** `link.py`
**Estimated Time:** 2-3 hours
**Dependency:** Phase 2.2 complete (wiki/ has classified notes)

#### Tasks

- [ ] **2.3.1** Create `load_embedding_model()` function
  - Load `all-MiniLM-L6-v2` from `sentence-transformers`
  - Cache the model in memory (load once, reuse)

- [ ] **2.3.2** Create `compute_embedding(note)` function
  - Combine: `title + " " + summary + " " + content[:500]`
  - Encode using the model
  - Return as Python list of floats (384 dimensions)

- [ ] **2.3.3** Create `embed_all_notes()` function
  - Scan all notes in `wiki/` (all PARA subdirectories)
  - Compute embedding for each note
  - Save embedding back into the note's JSON file (`"embedding": [0.123, ...]`)
  - Skip notes that already have embeddings (unless `--force`)

- [ ] **2.3.4** Add CLI entry point

```bash
python link.py embed               # compute embeddings for all
python link.py embed --force       # recompute all embeddings
```

---

### Phase 2.4 — Auto-Linking Related Notes

**File:** `link.py` (continued)
**Estimated Time:** 2-3 hours
**Dependency:** Phase 2.3 complete (notes have embeddings)

#### Tasks

- [ ] **2.4.1** Create `cosine_similarity(vec_a, vec_b)` function
  - Use `numpy` dot product / norms
  - Return float between -1 and 1

- [ ] **2.4.2** Create `find_related_notes(notes, threshold=0.65)` function
  - Build N×N similarity matrix
  - For each pair above threshold, create a link record:

```json
{
  "target_id": "cap_20260716_d4e5f6",
  "target_title": "Neural Network Fundamentals",
  "similarity": 0.78,
  "linked_at": "2026-07-16T20:35:00+05:30"
}
```

- [ ] **2.4.3** Create `update_links(notes, links)` function
  - Insert links bidirectionally (A→B and B→A)
  - Avoid duplicate links
  - Save updated notes back to `wiki/`

- [ ] **2.4.4** Create `link_all()` — full pipeline
  - Load all notes from `wiki/`
  - Ensure embeddings exist (call `embed_all_notes()` if missing)
  - Find related pairs
  - Update links
  - Print summary: `Found 12 links between 18 notes`

- [ ] **2.4.5** Add CLI entry point

```bash
python link.py                     # full pipeline: embed + link
python link.py link                # just linking (assumes embeddings exist)
python link.py link --threshold 0.7  # custom threshold
```

#### Auto-Linking Flow

```
  wiki/**/*.json (all classified notes)
         │
         ▼
  ┌──────────────────┐
  │ Load all notes   │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ Compute embeddings           │
  │ (if not already computed)    │
  │                              │
  │ Model: all-MiniLM-L6-v2     │
  │ Output: 384-dim float vector │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ Build N×N similarity matrix  │
  │                              │
  │ Note A  Note B  Similarity   │
  │ ──────  ──────  ──────────   │
  │ cap_01  cap_02    0.82       │
  │ cap_01  cap_03    0.45  ✗    │
  │ cap_02  cap_03    0.71       │
  │ cap_01  cap_04    0.68       │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ Filter: similarity > 0.65   │
  │ Insert bidirectional links   │
  │ Save to wiki/ JSON files     │
  └──────────────────────────────┘
           │
           ▼
      Result: 12 links found
      between 18 notes
```

---

### Phase 2.5 — Testing & Validation

**Estimated Time:** 1-2 hours

#### Tasks

- [ ] **2.5.1** Run classification on all 10+ raw captures
- [ ] **2.5.2** Verify each note lands in the correct PARA folder
- [ ] **2.5.3** Manually check 3-5 classifications for quality
- [ ] **2.5.4** Run auto-linking pipeline
- [ ] **2.5.5** Verify links make semantic sense (related topics linked)
- [ ] **2.5.6** Add 5+ more real captures to reach 15+ total
- [ ] **2.5.7** Re-run the full pipeline (classify → embed → link)

### Phase 2 — Acceptance Criteria

```
  ┌───────────────────────────────────────────────────────┐
  │  ✅ Phase 2 Complete When:                            │
  │                                                       │
  │  [ ] Any raw capture → category + tags + summary      │
  │  [ ] PARA categorization working correctly            │
  │  [ ] Embeddings computed per note (384-dim vectors)   │
  │  [ ] Related notes auto-linked (no manual tagging)    │
  │  [ ] Links are bidirectional                          │
  │  [ ] Runs on 15+ real items → organized wiki/         │
  │  [ ] LLM error handling + retry logic works           │
  │                                                       │
  │  🏅 Badge Earned: The Librarian                       │
  └───────────────────────────────────────────────────────┘
```

---

---

## Phase 3 — The Cartographer: Visualize the Brain (Week 3)

**🏅 Badge: The Cartographer**
**Goal:** Convert the wiki into a graph data model and render it as an interactive, explorable visualization.

---

### Phase 3.1 — Graph Data Builder

**File:** `build_graph.py`
**Estimated Time:** 2-3 hours
**Dependency:** Phase 2 complete (wiki/ has classified, linked notes)

#### Tasks

- [ ] **3.1.1** Create `load_all_notes()` function
  - Recursively scan `wiki/` subdirectories
  - Load each JSON file
  - Return list of note dicts

- [ ] **3.1.2** Create `build_nodes(notes)` function
  - For each note, create a node object:

```json
{
  "id": "cap_20260716_a3f8b2c1",
  "label": "Understanding Vector Emb...",
  "category": "resources",
  "tags": ["machine-learning", "embeddings"],
  "summary": "Overview of how vector embeddings...",
  "content_preview": "First 200 chars of content...",
  "created": "2026-07-16T20:30:00+05:30",
  "link_count": 3
}
```

  - Truncate label to 25 characters

- [ ] **3.1.3** Create `build_edges(notes)` function
  - Extract links from each note's `links[]` array
  - Deduplicate (A→B and B→A = 1 edge, not 2)
  - Create edge objects:

```json
{
  "source": "cap_20260716_a3f8b2c1",
  "target": "cap_20260716_d4e5f6",
  "similarity": 0.78
}
```

- [ ] **3.1.4** Create `build_graph()` — full pipeline
  - Load notes → Build nodes → Build edges → Assemble JSON:

```json
{
  "metadata": {
    "generated_at": "2026-07-16T20:40:00+05:30",
    "total_nodes": 18,
    "total_edges": 12
  },
  "nodes": [...],
  "edges": [...]
}
```

  - Write to `graph.json`

- [ ] **3.1.5** Add CLI entry point

```bash
python build_graph.py                # build graph.json
python build_graph.py --stats        # just print stats (nodes, edges, categories)
```

---

### Phase 3.2 — Interactive Graph Frontend (HTML + Cytoscape.js)

**File:** `graph_template.html` (HTML template with embedded JS)
**Estimated Time:** 4-5 hours
**Dependency:** Phase 3.1 complete (graph.json exists)

#### Tasks

- [ ] **3.2.1** Create the base HTML structure
  - Dark theme background (`#0a0a0a` or `#1a1a2e`)
  - Full-viewport canvas for the graph
  - Load Cytoscape.js from CDN

- [ ] **3.2.2** Implement node rendering
  - Color by PARA category:
    - 🟣 Projects → `#8B5CF6` (Purple)
    - 🔵 Areas → `#3B82F6` (Blue)
    - 🟢 Resources → `#10B981` (Green)
    - 🟠 Archives → `#F59E0B` (Orange)
  - Size proportional to `link_count` (more connections = larger)
  - Labels: truncated title (white text)

- [ ] **3.2.3** Implement edge rendering
  - Width proportional to `similarity` score
  - Color: semi-transparent gray `rgba(150,150,150,0.4)`
  - Curved edges for visual clarity

- [ ] **3.2.4** Implement hover popups (tooltips)
  - On node hover, show a tooltip with:
    - Note title (full)
    - Summary
    - Tags (as pills/badges)
    - Creation date
    - Number of connections

- [ ] **3.2.5** Implement interactions
  - Drag nodes to rearrange
  - Scroll to zoom in/out
  - Click node to highlight its connections
  - Double-click to center and zoom on a node

- [ ] **3.2.6** Implement force-directed layout
  - Use Cytoscape.js `cose` layout
  - Configure spring physics for natural clustering
  - Animate layout transitions

- [ ] **3.2.7** Add category legend overlay
  - Fixed position in corner
  - Shows color → category mapping

- [ ] **3.2.8** Add subtle animations
  - Gentle pulse/glow on nodes
  - Smooth edge animations on hover
  - Layout animation on load

#### Visual Reference

```
  ┌────────────────────────────────────────────────────────────────┐
  │  SecondSelf — Knowledge Graph                    [Legend ▼]    │
  │                                                                │
  │              ┌───┐                                             │
  │         ┌────│ R │────┐           ┌───┐                        │
  │         │    └───┘    │      ┌────│ P │                        │
  │       ┌───┐         ┌───┐   │    └───┘        Node Colors:    │
  │       │ R │─────────│ A │───┘                  🟣 Projects     │
  │       └───┘         └───┘                      🔵 Areas        │
  │         │              │          ┌───┐        🟢 Resources    │
  │         │            ┌───┐   ┌────│ AR│        🟠 Archives     │
  │         └────────────│ R │───┘    └───┘                        │
  │                      └───┘                                     │
  │                                                                │
  │  ┌──────────────────────────────────────────────────────┐      │
  │  │ HOVER TOOLTIP                                       │      │
  │  │ Title: Understanding Vector Embeddings              │      │
  │  │ Summary: Overview of how vector embeddings...       │      │
  │  │ Tags: [machine-learning] [embeddings] [nlp]         │      │
  │  │ Created: July 16, 2026 • 3 connections              │      │
  │  └──────────────────────────────────────────────────────┘      │
  └────────────────────────────────────────────────────────────────┘
```

---

### Phase 3.3 — Integration Testing

**Estimated Time:** 1-2 hours

#### Tasks

- [ ] **3.3.1** Regenerate `graph.json` from current wiki data
- [ ] **3.3.2** Open graph HTML in browser, verify all nodes render
- [ ] **3.3.3** Verify node colors match PARA categories
- [ ] **3.3.4** Test hover tooltips on 5+ nodes
- [ ] **3.3.5** Test drag, zoom, and click interactions
- [ ] **3.3.6** Verify edge count matches expected links
- [ ] **3.3.7** Test with different numbers of notes (5, 15, 30+)

### Phase 3 — Acceptance Criteria

```
  ┌───────────────────────────────────────────────────────┐
  │  ✅ Phase 3 Complete When:                            │
  │                                                       │
  │  [ ] build_graph.py produces valid graph.json         │
  │  [ ] graph.json has correct nodes + edges             │
  │  [ ] Interactive force-directed graph renders          │
  │  [ ] Nodes colored by PARA category                   │
  │  [ ] Hover reveals note content                       │
  │  [ ] Drag + zoom work smoothly                        │
  │  [ ] Built from your real notes, not dummy data       │
  │                                                       │
  │  🏅 Badge Earned: The Cartographer                    │
  └───────────────────────────────────────────────────────┘
```

---

---

## Phase 4 — The Oracle: Ask + Ship (Week 4)

**🏅 Badge: The Oracle**
**Goal:** Build RAG-powered Q&A over your notes, assemble everything into a Streamlit app, and deploy to a public URL.

---

### Phase 4.1 — RAG Pipeline (Retrieval-Augmented Generation)

**File:** `ask.py`
**Estimated Time:** 3-4 hours
**Dependency:** Phase 2 complete (notes have embeddings), LLM working

#### Tasks

- [ ] **4.1.1** Create `load_all_notes_with_embeddings()` function
  - Load all notes from `wiki/`
  - Filter to only notes with embeddings
  - Return list of note dicts

- [ ] **4.1.2** Create `embed_question(question)` function
  - Use same model as `link.py` (`all-MiniLM-L6-v2`)
  - Return 384-dim vector

- [ ] **4.1.3** Create `retrieve_relevant_notes(question, notes, top_k=5)` function
  - Embed the question
  - Compute cosine similarity against all note embeddings
  - Sort by similarity descending
  - Return top-K notes with similarity scores
  - If best similarity < 0.3, return empty (no relevant notes)

- [ ] **4.1.4** Create the RAG prompt template

```
SYSTEM: You are SecondSelf, a personal AI assistant that answers
questions using ONLY the user's personal notes.
Rules:
- Answer based ONLY on the provided notes
- Never make up information
- Cite which note(s) you used in your answer
- If the notes don't contain the answer, say so honestly

CONTEXT FROM USER'S NOTES:
---
Note 1: "{title_1}"
{content_1}
---
Note 2: "{title_2}"
{content_2}
---
(... up to K notes)

QUESTION: {user_question}

Provide a comprehensive answer based on the above notes.
Cite your sources by note title.
```

- [ ] **4.1.5** Create `ask(question, top_k=5)` function — full pipeline
  - Retrieve relevant notes
  - Build RAG prompt with context
  - Send to Groq LLM
  - Parse response
  - Return structured result:

```python
{
    "question": "What do I know about embeddings?",
    "answer": "Based on your notes, you captured...",
    "sources": [
        {"id": "cap_...", "title": "...", "similarity": 0.82},
        {"id": "cap_...", "title": "...", "similarity": 0.74}
    ],
    "confidence": "high"  # high (>0.7), medium (0.5-0.7), low (0.3-0.5)
}
```

- [ ] **4.1.6** Handle edge cases
  - No relevant notes → `"I don't have notes about this topic yet."`
  - LLM error → graceful fallback message
  - Empty wiki → `"Your brain is empty! Capture some notes first."`

- [ ] **4.1.7** Add CLI entry point

```bash
python ask.py "What do I know about machine learning?"
python ask.py "Summarize my project notes"
python ask.py "What links have I saved about Python?"
```

#### RAG Pipeline Flow

```
  "What do I know about embeddings?"
         │
         ▼
  ┌────────────────────┐
  │ Embed question     │──── all-MiniLM-L6-v2 ──── [0.12, 0.45, ...]
  └────────┬───────────┘
           │
           ▼
  ┌────────────────────────────────────┐
  │ Compare against all note vectors   │
  │                                    │
  │ Note: "Vector Embeddings"  → 0.82  │ ✓ Top-1
  │ Note: "Neural Networks"    → 0.74  │ ✓ Top-2
  │ Note: "Python Best Pracs"  → 0.61  │ ✓ Top-3
  │ Note: "Cooking Recipes"    → 0.12  │ ✗ Below threshold
  └────────┬───────────────────────────┘
           │
           ▼
  ┌────────────────────┐
  │ Build context:     │
  │ Top-3 note titles  │
  │ + content (1500    │
  │   chars each)      │
  └────────┬───────────┘
           │
           ▼
  ┌────────────────────┐     ┌──────────────────────┐
  │ RAG Prompt:        │────►│ Groq / Llama 3.3 70B │
  │ System + Context   │     └──────────┬───────────┘
  │ + Question         │                │
  └────────────────────┘                ▼
                               ┌──────────────────────────┐
                               │ "Based on your notes,    │
                               │  you have captured       │
                               │  several pieces about    │
                               │  embeddings..."          │
                               │                          │
                               │  Sources:                │
                               │  - Vector Embeddings     │
                               │  - Neural Networks       │
                               └──────────────────────────┘
```

---

### Phase 4.2 — Streamlit Application

**File:** `app.py`
**Estimated Time:** 4-5 hours
**Dependency:** All previous phases complete

#### Tasks

- [ ] **4.2.1** Set up base Streamlit app structure

```python
import streamlit as st

st.set_page_config(
    page_title="SecondSelf — AI Second Brain",
    page_icon="🧠",
    layout="wide"
)
```

- [ ] **4.2.2** Build the sidebar
  - **Capture Form:**
    - `st.text_area()` for content input
    - `st.selectbox()` for type (note/link/file)
    - `st.button("📥 Capture")` to trigger capture + classify + link
  - **Stats Dashboard:**
    - Total notes captured
    - Total auto-links
    - Notes per category (Projects / Areas / Resources / Archives)
  - **Settings:**
    - Similarity threshold slider (`st.slider()`, 0.3 - 0.9)
    - Top-K slider (`st.slider()`, 1 - 10)

- [ ] **4.2.3** Build Tab 1: Knowledge Graph
  - Load `graph.json`
  - Inject graph data into `graph_template.html`
  - Render using `st.components.v1.html(html_string, height=600)`
  - Add "🔄 Rebuild Graph" button

- [ ] **4.2.4** Build Tab 2: Ask Your Brain
  - `st.text_input("🔮 Ask your brain anything...")`
  - `st.button("Ask")`
  - Display answer in a styled card (`st.markdown()`)
  - Show source citations in `st.expander()` blocks
  - Show confidence indicator (high/medium/low with colored badge)

- [ ] **4.2.5** Build Tab 3: Browse Notes
  - Load all notes from `wiki/`
  - Display as `st.dataframe()` with columns: Title, Category, Tags, Date
  - Add filters: category dropdown, search text
  - Click to expand full note content

- [ ] **4.2.6** Wire up the sidebar capture form
  - On "Capture" button click:
    1. Run `capture.py` functions
    2. Run `classify.py` functions
    3. Run `link.py` functions
    4. Rebuild `graph.json`
    5. Show success toast

- [ ] **4.2.7** Style the app
  - Custom CSS via `st.markdown()` with `unsafe_allow_html=True`
  - Dark theme
  - Consistent colors matching graph node colors

#### Streamlit Layout

```
  ┌─── Sidebar ──────────────────┐ ┌─── Main Area ──────────────────────────┐
  │                               │ │                                        │
  │  🧠 SecondSelf                │ │  ┌─────────┬──────────┬──────────┐     │
  │                               │ │  │ 🗺️ Graph │ 🔮 Ask   │ 📚 Browse│     │
  │  ──────────────────────────   │ │  └─────────┴──────────┴──────────┘     │
  │                               │ │                                        │
  │  📥 Capture New               │ │  (Active Tab Content)                  │
  │  ┌──────────────────────┐     │ │                                        │
  │  │ Enter content...     │     │ │  ┌──────────────────────────────────┐  │
  │  │                      │     │ │  │                                  │  │
  │  │                      │     │ │  │     Interactive Graph /          │  │
  │  └──────────────────────┘     │ │  │     Ask Interface /              │  │
  │  Type: [Note ▼]               │ │  │     Notes Table                  │  │
  │  [📥 Capture]                 │ │  │                                  │  │
  │                               │ │  │                                  │  │
  │  ──────────────────────────   │ │  └──────────────────────────────────┘  │
  │                               │ │                                        │
  │  📊 Stats                     │ │                                        │
  │  Notes: 18                    │ │                                        │
  │  Links: 12                    │ │                                        │
  │  Categories: 4                │ │                                        │
  │                               │ │                                        │
  │  ──────────────────────────   │ │                                        │
  │                               │ │                                        │
  │  ⚙️ Settings                  │ │                                        │
  │  Threshold: [===●===] 0.65   │ │                                        │
  │  Top-K:     [==●=====] 5     │ │                                        │
  │                               │ │                                        │
  └───────────────────────────────┘ └────────────────────────────────────────┘
```

---

### Phase 4.3 — Local Testing

**Estimated Time:** 2-3 hours

#### Tasks

- [ ] **4.3.1** Run the Streamlit app locally

```bash
streamlit run app.py
```

- [ ] **4.3.2** Test full capture flow from sidebar
  - Capture a new note → verify it appears in Browse tab
  - Verify it gets classified and linked automatically

- [ ] **4.3.3** Test knowledge graph
  - Verify all nodes render
  - Test hover, drag, zoom
  - Verify colors match categories

- [ ] **4.3.4** Test Ask Your Brain
  - Ask 5 real questions about your captured notes
  - Verify answers cite correct sources
  - Test "no relevant notes" edge case
  - Test with empty question

- [ ] **4.3.5** Test Browse Notes
  - Verify all notes appear
  - Test category filter
  - Test search

---

### Phase 4.4 — Deployment

**Estimated Time:** 2-3 hours
**Dependency:** Phase 4.3 complete (app works locally)

#### Tasks

- [ ] **4.4.1** Prepare for deployment
  - Ensure `requirements.txt` is complete and up-to-date
  - Commit all data files (`wiki/`, `graph.json`) to Git
  - Ensure no hardcoded paths (use relative paths)

- [ ] **4.4.2** Push to GitHub

```bash
git add .
git commit -m "SecondSelf v1.0 — complete AI second brain"
git remote add origin https://github.com/<username>/secondself.git
git push -u origin main
```

- [ ] **4.4.3** Deploy to Streamlit Community Cloud
  1. Go to [share.streamlit.io](https://share.streamlit.io)
  2. Connect GitHub repository
  3. Select `app.py` as main file
  4. Add secrets: `GROQ_API_KEY = "gsk_..."`
  5. Deploy

  **OR** Deploy to HuggingFace Spaces:
  1. Create new Space (Streamlit SDK)
  2. Push code
  3. Set secrets in Space settings

- [ ] **4.4.4** Verify deployed app
  - Open the public URL
  - Test graph rendering
  - Test ask functionality
  - Test capture (if supported in deployment)
  - Share URL with a friend for feedback

#### Deployment Flow

```
  Local Development                     Cloud
  ─────────────────                     ─────

  ┌──────────┐     git push     ┌──────────────────┐
  │ Local    │──────────────────►│ GitHub Repo      │
  │ Project  │                   │ (public)         │
  └──────────┘                   └────────┬─────────┘
                                          │
                                          │ auto-deploy
                                          ▼
                                 ┌──────────────────┐
                                 │ Streamlit Cloud   │
                                 │                   │
                                 │ Reads:             │
                                 │  - app.py          │
                                 │  - requirements    │
                                 │  - wiki/ data      │
                                 │  - graph.json      │
                                 │                   │
                                 │ Secrets:           │
                                 │  - GROQ_API_KEY    │
                                 └────────┬─────────┘
                                          │
                                          ▼
                                 ┌──────────────────┐
                                 │ Public URL        │
                                 │ secondself.       │
                                 │ streamlit.app     │
                                 └──────────────────┘
```

---

### Phase 4.5 — README & Polish

**File:** `README.md`
**Estimated Time:** 1-2 hours

#### Tasks

- [ ] **4.5.1** Write README.md with:
  - Project title and description
  - Screenshot/GIF of the app
  - Features list
  - Tech stack
  - Setup instructions (local)
  - Environment variables
  - Usage examples
  - Live demo link

- [ ] **4.5.2** Final code cleanup
  - Add docstrings to all functions
  - Remove debug print statements
  - Ensure consistent code style

- [ ] **4.5.3** Final commit and push

### Phase 4 — Acceptance Criteria

```
  ┌───────────────────────────────────────────────────────┐
  │  ✅ Phase 4 Complete When:                            │
  │                                                       │
  │  [ ] ask() returns answers from your own notes        │
  │  [ ] Answers include source citations                 │
  │  [ ] Streamlit app has graph + search + browse        │
  │  [ ] Sidebar capture works end-to-end                 │
  │  [ ] Deployed live with a public URL                  │
  │  [ ] Full pipeline works in deployed app              │
  │  [ ] README with setup instructions exists            │
  │                                                       │
  │  🏅 Badge Earned: The Oracle                          │
  └───────────────────────────────────────────────────────┘
```

---

---

## Final Deliverables Checklist

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │  🎯 PROJECT COMPLETE WHEN:                                         │
  │                                                                     │
  │  [ ] Public GitHub repo with clean README + setup instructions      │
  │  [ ] Live deployed URL — graph + ask-your-brain, both working       │
  │  [ ] End-to-end flow verified:                                      │
  │      capture → classify → link → graph → ask                       │
  │  [ ] All 4 weekly badges earned:                                    │
  │      🏅 The Archivist (Week 1)                                     │
  │      🏅 The Librarian (Week 2)                                     │
  │      🏅 The Cartographer (Week 3)                                  │
  │      🏅 The Oracle (Week 4)                                        │
  │                                                                     │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## File Dependency Map

```
  config.py ◄───────────────────────────────────────────────────────┐
      │                                                              │
      ▼                                                              │
  capture.py ──── writes to ──── raw/*.json                          │
      │                              │                               │
      │                              ▼                               │
      │                         classify.py ──── writes to ──── wiki/**/*.json
      │                              │                               │
      │                              │    uses                       │
      │                              ▼                               │
      │                          link.py ──── updates ──── wiki/**/*.json
      │                              │                               │
      │                              │                               │
      │                              ▼                               │
      │                      build_graph.py ── writes to ── graph.json
      │                              │                               │
      │                              │                               │
      │                              ▼                               │
      │                          ask.py ──── reads ──── wiki/**/*.json
      │                              │                               │
      │                              │                               │
      ├──────────────────────────────┤                               │
      │                              │                               │
      ▼                              ▼                               │
  app.py (Streamlit) ─── imports ─── all above modules ──────────────┘
      │
      ▼
  graph_template.html ─── embedded in Streamlit via st.components
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Groq API rate limits | Medium | High | Implement backoff + Gemini fallback |
| Embedding model download slow | Low | Medium | Download once, cache locally |
| PDF extraction fails | Medium | Low | Catch errors, mark as "unprocessed" |
| Graph too large for browser | Low | Medium | Cap at 200 nodes, add filtering |
| Streamlit Cloud ephemeral storage | High | High | Commit data to repo, or use SQLite |
| LLM returns malformed JSON | Medium | Medium | Fallback regex parser + re-prompt |
| Duplicate notes | Medium | Low | Content hash deduplication in capture |
