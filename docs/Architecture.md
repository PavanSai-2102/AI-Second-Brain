# SecondSelf — Detailed System Architecture

A comprehensive architecture for building an AI-powered personal knowledge management system that captures, classifies, links, visualizes, and answers questions from your own notes.

---

## High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                   📥 CAPTURE LAYER (Week 1)                        │
│                                                                     │
│   User Input (note / link / file)                                   │
│            │                                                        │
│            ▼                                                        │
│       capture.py                                                    │
│            │                                                        │
│            ▼                                                        │
│      raw/ directory                                                 │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 🧠 INTELLIGENCE LAYER (Week 2)                      │
│                                                                     │
│      classify.py (PARA Sorting)                                     │
│            │                                                        │
│            ▼                                                        │
│      wiki/ directory  ◄──── link.py (Embedding + Auto-Linking)      │
│            │                                                        │
└────────────┼────────────────────────────────────────────────────────┘
             │
             ├──────────────────────────────┐
             ▼                              ▼
┌────────────────────────────────┐  ┌───────────────────────────────┐
│ 🗺️ VISUALIZATION (Week 3)      │  │ 🔮 QUERY LAYER (Week 4)       │
│                                │  │                               │
│   build_graph.py               │  │   ask.py (RAG Pipeline)       │
│        │                       │  │        │                      │
│        ▼                       │  │        ▼                      │
│   graph.json                   │  │   Streamlit UI (app.py) ◄─┐  │
│        │                       │  │        │                  │  │
│        ▼                       │  │        ▼                  │  │
│   Interactive Graph ───────────┼──┼──►  Public Deployment     │  │
│   (Cytoscape.js)               │  │                           │  │
└────────────────────────────────┘  └───────────────────────────┘  │
                                              ▲                     │
                                              └─────────────────────┘
```

---

## Detailed Component Architecture

---

### 1. Capture Layer — `capture.py` (Week 1)

**Purpose:** Single entry point to ingest any piece of information into the system.

#### Data Model — Raw Capture

Each capture is stored as a JSON file in `raw/`:

```json
{
  "id": "cap_20260716_a3f8b2c1",
  "timestamp": "2026-07-16T20:30:00+05:30",
  "type": "note | link | file",
  "title": "Auto-generated or user-provided title",
  "content": "The raw text / URL / file content",
  "source_file": "original_filename.pdf (if file upload)",
  "metadata": {
    "word_count": 142,
    "language": "en",
    "content_hash": "sha256:abc123..."
  }
}
```

#### File Naming Convention

```
raw/
├── 20260716_a3f8b2c1.json    # note
├── 20260716_b7d4e9f0.json    # link
├── 20260716_c1a2b3d4.json    # file (metadata)
└── attachments/
    └── c1a2b3d4_document.pdf  # original file preserved
```

#### Component Design

```
┌─── capture.py ──────────────────────────────────────────────────────┐
│                                                                     │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐        │
│  │ CLI Interface │    │ Content Detector │    │  Normalizer  │        │
│  │  (argparse)   │    │                 │    │              │        │
│  │               │    │ Auto-detect:    │    │ Strip HTML   │        │
│  │ --note "text" │───►│ URL → link      │───►│ Extract PDF  │──┐     │
│  │ --link "url"  │    │ path → file     │    │ Sanitize MD  │  │     │
│  │ --file "path" │    │ else → note     │    │              │  │     │
│  └──────────────┘    └─────────────────┘    └──────────────┘  │     │
│                                                               │     │
│  ┌──────────────────────────────────────────────────────────┐  │     │
│  │                        Writer                            │◄─┘     │
│  │  Generate UUID + timestamp → Write JSON → Copy attachments│       │
│  └─────────────────────────────┬────────────────────────────┘        │
│                                │                                     │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                                 ▼
                            ┌─────────┐
                            │  raw/   │
                            └─────────┘
```

| Sub-Component | Responsibility |
|---|---|
| **CLI Interface** | Parse `--note "text"`, `--link "url"`, `--file "path"` arguments |
| **Content Detector** | Auto-detect type if not specified (URL regex → link, file path → file, else → note) |
| **Normalizer** | Strip HTML from links (use `requests` + `BeautifulSoup`), extract text from PDFs (`PyPDF2`), sanitize markdown |
| **Writer** | Generate UUID, timestamp, write JSON to `raw/`, copy attachments |

#### Key Design Decisions

- **JSON over Markdown for raw storage:** Machine-readable, schema-enforceable, easy to parse downstream.
- **Content hashing:** Prevent duplicate captures by checking `content_hash` before writing.
- **Attachment separation:** Binary files stored in `raw/attachments/`, metadata JSON references them. Keeps the metadata clean and scannable.

---

### 2. Intelligence Layer — `classify.py` + `link.py` (Week 2)

#### 2.1 Classification Engine — `classify.py`

**Purpose:** Send each raw capture to an LLM for PARA classification, tagging, and summarization.

#### PARA Framework Mapping

| Category | Definition | Example |
|---|---|---|
| **Projects** | Active, time-bound goals | "Build SecondSelf app" |
| **Areas** | Ongoing responsibilities | "Machine Learning study", "Health" |
| **Resources** | Reference material for future use | "Python best practices", "API docs" |
| **Archives** | Inactive/completed items | "Old project notes", "Finished course" |

#### Classification Pipeline

```
  ┌──────────────┐
  │ raw/*.json   │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ Batch Loader │  (Load all raw captures)
  └──────┬───────┘
         │
         ▼
  ┌────────────────┐
  │ Prompt Builder │  (Construct classification prompt)
  └──────┬─────────┘
         │
         ▼
  ┌──────────────────────────┐     ┌──────────────────────────────────┐
  │ Groq API (Llama 3.3 70B) │     │ PROMPT TEMPLATE:                 │
  │                          │◄────│ "You are a knowledge organizer   │
  │ Send content for         │     │  using the PARA method.           │
  │ classification           │     │  Classify this content: {content} │
  └──────────┬───────────────┘     │  Respond in JSON:                │
             │                     │  {category, tags[], summary,     │
             ▼                     │   suggested_title}"               │
  ┌─────────────────┐              └──────────────────────────────────┘
  │ Response Parser │  (Extract JSON from LLM response)
  └──────┬──────────┘
         │
         ▼
  ┌───────────────┐
  │ Enriched Note │  (Original content + category + tags + summary)
  └──────┬────────┘
         │
         ▼
  ┌──────────────────────┐
  │ wiki/{para_category}/│  (Save to Projects/Areas/Resources/Archives)
  └──────────────────────┘
```

#### Classified Note Data Model (stored in `wiki/`)

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
  "summary": "Overview of how vector embeddings represent semantic meaning in NLP.",
  "links": [],
  "embedding": null
}
```

#### Wiki Directory Structure

```
wiki/
├── projects/
│   └── cap_20260716_x1y2z3.json
├── areas/
│   └── cap_20260716_a1b2c3.json
├── resources/
│   ├── cap_20260716_a3f8b2c1.json
│   └── cap_20260716_d4e5f6.json
└── archives/
    └── cap_20260716_m7n8o9.json
```

#### LLM Integration Details

| Aspect | Choice | Rationale |
|---|---|---|
| **Provider** | Groq (free tier) | Fast inference, generous free tier (30 req/min) |
| **Model** | Llama 3.3 70B | Best open-source quality for classification |
| **Fallback** | Google Gemini Flash | If Groq rate-limits, fall back to Gemini free tier |
| **Response format** | Structured JSON mode | Reliable parsing, no regex needed |
| **Rate limiting** | `time.sleep(2)` between calls | Stay within free tier |
| **Error handling** | Retry 3× with exponential backoff | Handle transient API failures |

---

#### 2.2 Auto-Linking Engine — `link.py`

**Purpose:** Compute semantic embeddings for every note and automatically discover + insert links between related notes.

#### Embedding Pipeline

```
  ┌──────────────────┐
  │ wiki/**/*.json   │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  Load all notes  │
  └────────┬─────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Compute Embeddings    │  (sentence-transformers, all-MiniLM-L6-v2)
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────────┐
  │ Store embedding in note    │  (384-dim float array → JSON)
  └────────┬───────────────────┘
           │
           ▼
  ┌────────────────────────────┐
  │ Pairwise Cosine Similarity │  (N×N matrix comparison)
  └────────┬───────────────────┘
           │
           ▼
     ┌─────────────┐
     │ similarity   │
     │  > 0.65 ?    │
     └──┬───────┬───┘
        │       │
     YES│       │NO
        ▼       ▼
  ┌──────────┐  (Skip)
  │ Insert   │
  │ bidirect.│
  │ link     │
  └────┬─────┘
       │
       ▼
  ┌──────────────────────────┐
  │ Update both notes'       │
  │ links[] arrays           │
  └──────────────────────────┘
```

#### Embedding Model Choice

| Aspect | Choice | Rationale |
|---|---|---|
| **Library** | `sentence-transformers` | Industry standard, runs locally, free |
| **Model** | `all-MiniLM-L6-v2` | 384-dim vectors, fast, good quality for semantic search |
| **Input** | `title + " " + summary + " " + content[:500]` | Balanced between richness and token limits |
| **Storage** | Embedded in each note's JSON as a float array | Simple, no external vector DB needed |
| **Similarity** | Cosine similarity via `numpy` | Standard for semantic comparison |
| **Threshold** | `0.65` (configurable) | Empirically good balance: enough links without noise |

#### Link Data Structure

Each note's `links` array stores bidirectional references:

```json
{
  "links": [
    {
      "target_id": "cap_20260716_d4e5f6",
      "target_title": "Neural Network Fundamentals",
      "similarity": 0.78,
      "linked_at": "2026-07-16T20:35:00+05:30"
    }
  ]
}
```

#### Similarity Index (optimization for scale)

For 15+ notes, brute-force pairwise comparison is fine. At scale, use a FAISS flat index:

```python
# link.py — core logic sketch
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
THRESHOLD = 0.65

def compute_embedding(note: dict) -> list[float]:
    text = f"{note['title']} {note['summary']} {note['content'][:500]}"
    return model.encode(text).tolist()

def find_links(notes: list[dict]) -> list[tuple[str, str, float]]:
    embeddings = np.array([n['embedding'] for n in notes])
    # Cosine similarity matrix
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    sim_matrix = (embeddings @ embeddings.T) / (norms @ norms.T)
    
    links = []
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            if sim_matrix[i][j] > THRESHOLD:
                links.append((notes[i]['id'], notes[j]['id'], float(sim_matrix[i][j])))
    return links
```

---

### 3. Visualization Layer — `build_graph.py` + Frontend (Week 3)

#### 3.1 Graph Data Builder — `build_graph.py`

**Purpose:** Read all wiki notes and their links, produce a clean `graph.json` for the frontend.

#### Graph JSON Schema

```json
{
  "metadata": {
    "generated_at": "2026-07-16T20:40:00+05:30",
    "total_nodes": 18,
    "total_edges": 12
  },
  "nodes": [
    {
      "id": "cap_20260716_a3f8b2c1",
      "label": "Understanding Vector Embeddings",
      "category": "resources",
      "tags": ["machine-learning", "embeddings"],
      "summary": "Overview of how vector embeddings...",
      "content_preview": "First 200 chars of content...",
      "created": "2026-07-16T20:30:00+05:30"
    }
  ],
  "edges": [
    {
      "source": "cap_20260716_a3f8b2c1",
      "target": "cap_20260716_d4e5f6",
      "similarity": 0.78
    }
  ]
}
```

#### Graph Builder Pipeline

```
                                    ┌───────────────────┐
                               ┌───►│  Build node list   │───┐
                               │    └───────────────────┘   │
  ┌──────────────┐   ┌─────────┴──┐                         │   ┌──────────────┐   ┌────────────┐
  │wiki/**/*.json│──►│ Scan all   │                         ├──►│ Merge into   │──►│ graph.json │
  └──────────────┘   │ notes      │                         │   │ graph.json   │   └────────────┘
                     └─────────┬──┘                         │   └──────────────┘
                               │    ┌───────────────────┐   │
                               └───►│ Extract unique     │───┘
                                    │ edges from links[] │
                                    └───────────────────┘
```

---

#### 3.2 Interactive Graph Frontend

**Purpose:** Render the knowledge graph as a living, explorable visualization.

#### Technology: Cytoscape.js

| Aspect | Choice | Rationale |
|---|---|---|
| **Library** | Cytoscape.js | More powerful than vis-network, better styling, widely used in bioinformatics/knowledge graphs |
| **Layout** | `cose` (Compound Spring Embedder) | Force-directed, handles clusters well |
| **Rendering** | Canvas-based | Performant for 100+ nodes |

#### Visual Design Specification

```
  ┌─── Node Styling by PARA Category ──────────────────┐
  │                                                     │
  │   🟣  Projects  ── Purple  (#8B5CF6)                │
  │   🔵  Areas     ── Blue    (#3B82F6)                │
  │   🟢  Resources ── Green   (#10B981)                │
  │   🟠  Archives  ── Orange  (#F59E0B)                │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

| Element | Visual Property |
|---|---|
| **Node size** | Proportional to number of links (more connected = larger) |
| **Node color** | PARA category (see above) |
| **Node label** | Truncated title (max 25 chars) |
| **Edge width** | Proportional to similarity score |
| **Edge color** | Semi-transparent gray (`rgba(150,150,150,0.4)`) |
| **Hover popup** | Note title, summary, tags, creation date |
| **Animation** | Subtle pulse on nodes, smooth spring physics |

#### Frontend Integration with Streamlit

The graph is rendered inside a Streamlit app using `streamlit.components.v1.html()`:

```
app.py
├── Loads graph.json
├── Injects it into an HTML template containing Cytoscape.js
├── Renders via st.components.v1.html(html_string, height=600)
```

---

### 4. Query Layer — `ask.py` + `app.py` (Week 4)

#### 4.1 RAG Pipeline — `ask.py`

**Purpose:** Answer natural-language questions using Retrieval-Augmented Generation over your personal knowledge base.

#### RAG Architecture

```
  ┌───────────────────┐
  │  User Question    │  "What do I know about embeddings?"
  └────────┬──────────┘
           │
           ▼
  ┌─────────────────────────┐
  │ Embed question          │  (all-MiniLM-L6-v2 — same model as link.py)
  └────────┬────────────────┘
           │
           ▼
  ┌─────────────────────────────┐
  │ Cosine similarity vs all    │  (Compare question vector against
  │ note embeddings             │   every note's stored embedding)
  └────────┬────────────────────┘
           │
           ▼
  ┌─────────────────────────┐
  │ Top-K relevant notes    │  (K=5, configurable)
  │ (ranked by similarity)  │
  └────────┬────────────────┘
           │
           ▼
  ┌─────────────────────────┐
  │ Build context window    │  (Concatenate top-K notes, truncated
  │                         │   to 1500 chars each)
  └────────┬────────────────┘
           │
           ▼
  ┌──────────────────────┐     ┌──────────────────────────────────────┐
  │ Construct RAG prompt │────►│ PROMPT TEMPLATE:                     │
  └──────────┬───────────┘     │ "You are SecondSelf. Answer using    │
             │                 │  ONLY the user's personal notes.     │
             │                 │  Never make up information.          │
             │                 │                                      │
             │                 │  Context from user's notes:          │
             │                 │  --- Note 1: {title} ---             │
             │                 │  {content}                           │
             │                 │  --- Note 2: {title} ---             │
             │                 │  {content}                           │
             │                 │                                      │
             │                 │  Question: {user_question}           │
             │                 │  Answer & cite which note(s) used."  │
             ▼                 └──────────────────────────────────────┘
  ┌──────────────────────────┐
  │ Groq / Llama 3.3 70B     │
  └──────────┬───────────────┘
             │
             ▼
  ┌──────────────────────────────────┐
  │ Synthesized answer with          │
  │ source citations                 │
  └──────────────────────────────────┘
```

#### Retrieval Strategy

| Aspect | Design |
|---|---|
| **Embedding model** | Same `all-MiniLM-L6-v2` (consistency with link.py) |
| **Search method** | Cosine similarity over all note embeddings |
| **Top-K** | 5 notes (configurable) |
| **Context window** | Concatenate top-K notes' full content (truncated to 1500 chars each) |
| **Total context limit** | ~7500 chars to stay within LLM context limits on free tier |
| **No-result handling** | If best similarity < 0.3, respond "I don't have notes about this topic" |

#### `ask()` Function Signature

```python
def ask(question: str, top_k: int = 5) -> dict:
    """
    Returns:
    {
        "question": "What do I know about embeddings?",
        "answer": "Based on your notes, you captured...",
        "sources": [
            {"id": "cap_...", "title": "...", "similarity": 0.82},
            {"id": "cap_...", "title": "...", "similarity": 0.74}
        ],
        "confidence": "high"  # high/medium/low based on top similarity
    }
    """
```

---

#### 4.2 Streamlit Application — `app.py`

**Purpose:** Unified UI combining the knowledge graph and ask-anything search.

#### Page Layout

```
┌──────────────────────────────────────────────────┐
│  🧠 SecondSelf — Your AI Second Brain            │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌─── Sidebar ───────────────────────┐           │
│  │ 📥 Capture New Note               │           │
│  │ [text input + type selector]      │           │
│  │ [Capture button]                  │           │
│  │                                   │           │
│  │ 📊 Stats                          │           │
│  │  • 18 notes captured              │           │
│  │  • 12 auto-links                  │           │
│  │  • 4 categories                   │           │
│  │                                   │           │
│  │ ⚙️ Settings                       │           │
│  │  • Similarity threshold slider    │           │
│  │  • Top-K slider                   │           │
│  └───────────────────────────────────┘           │
│                                                  │
│  ┌─── Main Area ────────────────────────────┐    │
│  │  Tab 1: 🗺️ Knowledge Graph               │    │
│  │  [Interactive Cytoscape.js graph]        │    │
│  │                                          │    │
│  │  Tab 2: 🔮 Ask Your Brain                │    │
│  │  [Search bar: "Ask anything..."]         │    │
│  │  [Answer card with source citations]     │    │
│  │                                          │    │
│  │  Tab 3: 📚 Browse Notes                  │    │
│  │  [Filterable table of all notes]         │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Streamlit Components

| Component | Implementation |
|---|---|
| **Knowledge Graph** | `st.components.v1.html()` with Cytoscape.js embedded |
| **Search Bar** | `st.text_input()` + `st.button()` |
| **Answer Display** | `st.markdown()` with styled cards |
| **Source Citations** | `st.expander()` for each cited note |
| **Capture Form** | `st.text_area()` + `st.selectbox()` + `st.button()` in sidebar |
| **Stats** | `st.metric()` cards |
| **Note Browser** | `st.dataframe()` with filters |

---

## Technology Stack Summary

| Layer | Technology | Version / Notes |
|---|---|---|
| **Language** | Python | 3.10+ |
| **Capture** | `argparse`, `requests`, `beautifulsoup4`, `PyPDF2` | CLI + content extraction |
| **LLM Provider** | Groq API (free tier) | `groq` Python SDK |
| **LLM Model** | Llama 3.3 70B | Via Groq |
| **Embeddings** | `sentence-transformers` | `all-MiniLM-L6-v2` (local, free) |
| **Similarity** | `numpy` | Cosine similarity |
| **Graph Viz** | Cytoscape.js | Embedded in Streamlit via HTML component |
| **UI Framework** | Streamlit | `streamlit >= 1.30` |
| **Deployment** | Streamlit Community Cloud or HuggingFace Spaces | Free hosting |
| **Version Control** | Git + GitHub | Public repo |

---

## `requirements.txt`

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

---

## Configuration & Environment

```
.env (NEVER committed — add to .gitignore)
├── GROQ_API_KEY=gsk_...
└── SIMILARITY_THRESHOLD=0.65

config.py
├── Load .env
├── PARA_CATEGORIES = ["projects", "areas", "resources", "archives"]
├── EMBEDDING_MODEL = "all-MiniLM-L6-v2"
├── TOP_K = 5
├── MAX_CONTENT_LENGTH = 1500
└── SIMILARITY_THRESHOLD = 0.65
```

---

## Data Flow — End to End

```
  User          capture.py      raw/       classify.py    Groq LLM      wiki/
   │                │             │             │             │             │
   │  Input note    │             │             │             │             │
   │  /link/file    │             │             │             │             │
   │───────────────►│             │             │             │             │
   │                │  Save JSON  │             │             │             │
   │                │  + attach.  │             │             │             │
   │                │────────────►│             │             │             │
   │                │             │             │             │             │
   │                │             │  Read raw   │             │             │
   │                │             │────────────►│             │             │
   │                │             │             │  Send for   │             │
   │                │             │             │  classify   │             │
   │                │             │             │────────────►│             │
   │                │             │             │  {category, │             │
   │                │             │             │◄─tags,sum}──│             │
   │                │             │             │  Save note  │             │
   │                │             │             │────────────────────────►  │
   │                │             │             │             │             │
   │                │             │             │             │             │
  link.py      Embed Model    build_graph.py   graph.json    app.py      ask.py
   │                │             │             │             │             │
   │  Load all      │             │             │             │             │
   │  notes from    │             │             │             │             │
   │  wiki/         │             │             │             │             │
   │                │             │             │             │             │
   │  Compute       │             │             │             │             │
   │  embeddings    │             │             │             │             │
   │───────────────►│             │             │             │             │
   │◄──384-dim──────│             │             │             │             │
   │  vectors       │             │             │             │             │
   │                │             │             │             │             │
   │  Pairwise cosine similarity  │             │             │             │
   │  Update links[] in wiki/     │             │             │             │
   │                │             │             │             │             │
   │                │  Read notes │             │             │             │
   │                │  + links    │             │             │             │
   │                │────────────►│  Export      │             │             │
   │                │             │  nodes+edges│             │             │
   │                │             │────────────►│             │             │
   │                │             │             │             │             │
   │                │             │             │  Load graph │             │
   │                │             │             │────────────►│             │
   │                │             │             │             │  User asks  │
   │                │             │             │             │  a question │
   │                │             │             │             │────────────►│
   │                │             │             │             │             │
   │                │  Embed      │             │             │             │
   │                │◄─question───│             │             │             │
   │                │             │             │             │  Find top-K │
   │                │             │             │             │  from wiki/ │
   │                │             │             │             │             │
   │                │             │             │             │  RAG prompt │
   │                │             │             │             │  + context  │
   │                │             │             │             │  → Groq LLM │
   │                │             │             │             │             │
   │                │             │             │             │  Answer +   │
   │                │             │             │             │◄─sources────│
   │                │             │             │             │             │
   │                │             │             │  Display answer with      │
   │                │             │             │  citations to user        │
```

---

## Deployment Architecture

```
  ┌─── GitHub Repository ──────────────┐
  │                                     │
  │  ┌─────────────┐                    │
  │  │ Source Code  │───────────┐       │
  │  └─────────────┘            │       │
  │  ┌──────────────────────┐   │       │
  │  │ wiki/ + graph.json   │───┤       │
  │  │ (committed data)     │   │       │
  │  └──────────────────────┘   │       │
  │  ┌──────────────────┐      │       │
  │  │ requirements.txt  │──────┤       │
  │  └──────────────────┘      │       │
  └─────────────────────────────┼───────┘
                                │
                                ▼
  ┌─── Streamlit Community Cloud ───────────────────────┐
  │                                                      │
  │  ┌─────────────────────┐                             │
  │  │ Auto-deploy from    │                             │
  │  │ GitHub              │                             │
  │  └──────────┬──────────┘                             │
  │             │                                        │
  │             ▼                                        │
  │  ┌─────────────────────┐    ┌──────────────────────┐ │
  │  │ Running Streamlit   │◄───│ Streamlit Secrets     │ │
  │  │ App                 │    │ Manager (API keys)    │ │
  │  └──────────┬──────────┘    └──────────────────────┘ │
  │             │                                        │
  │             ▼                                        │
  │  ┌─────────────────────────────────┐                 │
  │  │ https://secondself.streamlit.app │                 │
  │  └─────────────────────────────────┘                 │
  └──────────────────────┬───────────────────────────────┘
                         │
                         │ API Calls
                         ▼
               ┌──────────────────┐
               │ Groq API         │
               │ (free tier)      │
               └──────────────────┘
```

> [!IMPORTANT]
> **API Keys:** Store `GROQ_API_KEY` in Streamlit's Secrets Manager for deployment (not in `.env` or code). Locally, use `.env` with `python-dotenv`.

---

## Error Handling & Edge Cases

| Scenario | Handling |
|---|---|
| Duplicate capture | Check `content_hash` — skip with warning if duplicate exists |
| LLM API rate limit | Exponential backoff (2s, 4s, 8s), max 3 retries, then queue for later |
| LLM returns malformed JSON | Fallback regex parser, or re-prompt with stricter instructions |
| Empty content | Reject with user-friendly error message |
| PDF extraction fails | Catch `PyPDF2` errors, store raw file path, mark as "unprocessed" |
| No related notes found (linking) | Note gets empty `links[]` — that's fine, it's an island node |
| Question has no relevant notes | Return "I don't have notes about this topic" if best similarity < 0.3 |
| Graph too large for browser | Limit to 200 nodes in view, add pagination/filtering |

---

## Testing Strategy

| Week | Test Type | What to Test |
|---|---|---|
| **Week 1** | Manual + Unit | Capture 10+ real items, verify JSON schema, check deduplication |
| **Week 2** | Integration | Run classification on all raw items, verify PARA categories make sense, check link quality |
| **Week 3** | Visual | Load graph in browser, verify all nodes/edges appear, test hover/drag/zoom |
| **Week 4** | End-to-End | Ask 5 real questions, verify answers cite correct sources, deploy and test public URL |

---

## Open Questions

> [!IMPORTANT]
> **LLM Provider:** The plan uses Groq (free tier with Llama 3.3 70B). Do you already have a Groq API key, or would you prefer to use a different free LLM provider (e.g., Google Gemini, OpenRouter)?

> [!IMPORTANT]
> **Scope of Week 1:** Should the capture script also support capturing from clipboard / browser bookmarks, or is CLI-only sufficient for the first week?

> [!IMPORTANT]
> **Deployment platform preference:** Streamlit Community Cloud (easiest) vs. HuggingFace Spaces (more flexible)? Both are free.

> [!NOTE]
> **Data persistence in deployment:** On Streamlit Cloud, the filesystem is ephemeral. The wiki data and graph.json would need to be committed to the repo or backed by a lightweight database (SQLite / JSON on GitHub). The architecture above assumes data is committed to the repo for simplicity.
