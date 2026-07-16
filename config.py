"""
SecondSelf — Centralized Configuration

All project-wide constants, paths, and environment variables are loaded here.
Import this module in any script: `from config import *` or `import config`
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Load environment variables from .env file
# ──────────────────────────────────────────────
load_dotenv()

# ──────────────────────────────────────────────
# Project Root (directory where config.py lives)
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()

# ──────────────────────────────────────────────
# API Keys
# ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ──────────────────────────────────────────────
# Directory Paths
# ──────────────────────────────────────────────
RAW_DIR = PROJECT_ROOT / "raw"
WIKI_DIR = PROJECT_ROOT / "wiki"
ATTACHMENTS_DIR = RAW_DIR / "attachments"
GRAPH_JSON_PATH = PROJECT_ROOT / "graph.json"

# ──────────────────────────────────────────────
# PARA Categories
# ──────────────────────────────────────────────
PARA_CATEGORIES = ["projects", "areas", "resources", "archives"]

# ──────────────────────────────────────────────
# LLM Settings
# ──────────────────────────────────────────────
LLM_MODEL = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1024
LLM_RETRY_ATTEMPTS = 3
LLM_RETRY_BASE_DELAY = 2  # seconds (exponential: 2s, 4s, 8s)
LLM_RATE_LIMIT_DELAY = 2  # seconds between API calls

# ──────────────────────────────────────────────
# Embedding Settings
# ──────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.65"))

# ──────────────────────────────────────────────
# RAG (Retrieval-Augmented Generation) Settings
# ──────────────────────────────────────────────
TOP_K = 5
MAX_CONTENT_LENGTH = 1500  # chars per note in RAG context
MAX_RAW_CONTENT = 5000     # chars to send for classification
MIN_SIMILARITY_FOR_ANSWER = 0.3  # below this, "no relevant notes"

# ──────────────────────────────────────────────
# Capture Settings
# ──────────────────────────────────────────────
MAX_FILE_SIZE_MB = 50
URL_FETCH_TIMEOUT = 15  # seconds
SUPPORTED_FILE_TYPES = [".txt", ".md", ".pdf"]

# ──────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────

def validate_config():
    """Check that essential directories exist and config is sane."""
    errors = []

    # Check directories exist
    for d in [RAW_DIR, WIKI_DIR, ATTACHMENTS_DIR]:
        if not d.exists():
            errors.append(f"Directory not found: {d}")

    for category in PARA_CATEGORIES:
        cat_dir = WIKI_DIR / category
        if not cat_dir.exists():
            errors.append(f"PARA directory not found: {cat_dir}")

    # Check threshold range
    if not (0.3 <= SIMILARITY_THRESHOLD <= 0.95):
        errors.append(
            f"SIMILARITY_THRESHOLD={SIMILARITY_THRESHOLD} out of range [0.3, 0.95]. "
            f"Using default 0.65."
        )

    if errors:
        print("⚠️  Configuration warnings:")
        for e in errors:
            print(f"   - {e}")
        return False

    return True


if __name__ == "__main__":
    print("SecondSelf — Configuration Check")
    print("=" * 40)
    print(f"Project Root:    {PROJECT_ROOT}")
    print(f"Raw Dir:         {RAW_DIR}")
    print(f"Wiki Dir:        {WIKI_DIR}")
    print(f"Attachments Dir: {ATTACHMENTS_DIR}")
    print(f"Graph JSON:      {GRAPH_JSON_PATH}")
    print()
    print(f"GROQ_API_KEY:    {'✅ Set' if GROQ_API_KEY and GROQ_API_KEY != 'gsk_your_key_here' else '❌ Not set'}")
    print(f"LLM Model:       {LLM_MODEL}")
    print(f"Embed Model:     {EMBEDDING_MODEL}")
    print(f"Similarity:      {SIMILARITY_THRESHOLD}")
    print(f"Top-K:           {TOP_K}")
    print()

    if validate_config():
        print("✅ All configuration checks passed!")
    else:
        print("\n❌ Some checks failed. Fix the issues above.")
