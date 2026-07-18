"""
SecondSelf — RAG Pipeline (Phase 4: The Oracle)

Retrieval-Augmented Generation (RAG) module. Embeds a user's question,
retrieves the most relevant notes via cosine similarity, and queries the LLM
to generate a contextual answer.

Usage:
    python ask.py "What do I know about machine learning?"
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Try to reuse imports from other modules
import config
from classify import get_llm_client
from link import get_model, cosine_similarity


# ──────────────────────────────────────────────
# 4.1.1 — Load Notes
# ──────────────────────────────────────────────

def load_all_notes_with_embeddings() -> list[dict]:
    """Load all notes from wiki/ that possess an embedding vector."""
    notes = []
    if not config.WIKI_DIR.exists():
        return notes
        
    for json_file in config.WIKI_DIR.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Must have a valid embedding
            emb = data.get("embedding")
            if emb and len(emb) == config.EMBEDDING_DIMENSION:
                notes.append(data)
                
        except (json.JSONDecodeError, OSError):
            continue
            
    return notes


# ──────────────────────────────────────────────
# 4.1.2 — Embed Question
# ──────────────────────────────────────────────

def embed_question(question: str) -> list[float]:
    """Generate 384-dim embedding for the user's question."""
    # Truncate to prevent excessively long questions (EC-4.1.4)
    if len(question) > 500:
        question = question[:500]
        
    model = get_model()
    # encode() returns numpy array, convert to list
    return model.encode(question).tolist()


# ──────────────────────────────────────────────
# 4.1.3 — Retrieve Relevant Notes
# ──────────────────────────────────────────────

def retrieve_relevant_notes(question_emb: list[float], notes: list[dict], top_k: int = 5) -> list[dict]:
    """Find the top_k most similar notes to the question embedding."""
    results = []
    
    for note in notes:
        sim = cosine_similarity(question_emb, note["embedding"])
        # Only consider somewhat relevant notes
        if sim > 0.3:
            results.append({
                "note": note,
                "similarity": sim
            })
            
    # Sort by descending similarity
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


# ──────────────────────────────────────────────
# 4.1.4 — LLM Request Generation
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are SecondSelf, a personal AI assistant that answers questions using ONLY the user's personal notes.
Rules:
- Answer based ONLY on the provided notes context.
- Never make up information.
- Cite which note(s) you used in your answer.
- If the notes don't contain the answer, say so honestly."""

def call_llm_text(client, system_prompt: str, user_prompt: str) -> str:
    """Standard LLM call returning raw text (no JSON forcing)."""
    retries = config.LLM_RETRY_ATTEMPTS
    delay = config.LLM_RETRY_BASE_DELAY

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3, # Lower temp for factual RAG
                max_tokens=config.LLM_MAX_TOKENS,
                timeout=30.0
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️  LLM Error: {e}. Retrying... ({attempt+1}/{retries})")
            time.sleep(delay)
            delay *= 2
            
    return "❌ Error: Could not get a response from the AI after multiple attempts."


# ──────────────────────────────────────────────
# 4.1.5 — Main Ask Pipeline
# ──────────────────────────────────────────────

def ask(question: str, top_k: int = 5) -> dict:
    """Full RAG Pipeline. Returns structured dict."""
    
    # 1. Edge Case: Empty Question (EC-4.1.1)
    if not question.strip():
        return {
            "question": question,
            "answer": "Please enter a question.",
            "sources": [],
            "confidence": "none"
        }
        
    print(f"🔍 Searching brain for: '{question}'...")
        
    # 2. Load Notes
    notes = load_all_notes_with_embeddings()
    if not notes:
        return {
            "question": question,
            "answer": "Your brain is empty! Capture some notes first, then run `python link.py`.",
            "sources": [],
            "confidence": "none"
        }
        
    # 3. Embed and Retrieve
    question_emb = embed_question(question)
    top_results = retrieve_relevant_notes(question_emb, notes, top_k)
    
    # Edge Case: No relevant notes found (EC-4.1.2)
    if not top_results:
        return {
            "question": question,
            "answer": "I don't have any notes about this topic yet. Try capturing some content about it first!",
            "sources": [],
            "confidence": "none"
        }
        
    # 4. Build Context
    context_blocks = []
    sources = []
    max_sim = top_results[0]["similarity"]
    
    for idx, res in enumerate(top_results, 1):
        note = res["note"]
        sim = res["similarity"]
        
        # Track for source citation metadata
        sources.append({
            "id": note["id"],
            "title": note["title"],
            "similarity": round(sim, 3)
        })
        
        # Truncate content to avoid blowing up context window
        content = note.get("content", "")
        if len(content) > 1500:
            content = content[:1500] + "... [truncated]"
            
        context_blocks.append(
            f"Note {idx}: \"{note['title']}\"\n{content}\n"
        )
        
    context_str = "---\n" + "\n---\n".join(context_blocks) + "\n---"
    
    user_prompt = f"""CONTEXT FROM USER'S NOTES:
{context_str}

QUESTION: {question}

Provide a comprehensive answer based on the above notes. 
Cite your sources by note title. If the notes don't contain the answer, say so honestly."""

    # 5. Call LLM
    print("🧠 Generating answer...")
    client = get_llm_client()
    answer_text = call_llm_text(client, SYSTEM_PROMPT, user_prompt)
    
    # Determine confidence based on top similarity
    confidence = "low"
    if max_sim > 0.7:
        confidence = "high"
    elif max_sim > 0.5:
        confidence = "medium"

    return {
        "question": question,
        "answer": answer_text.strip(),
        "sources": sources,
        "confidence": confidence
    }


# ──────────────────────────────────────────────
# CLI Interface
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SecondSelf — Ask Your Brain (The Oracle)"
    )
    parser.add_argument("question", type=str, help="The question to ask")
    parser.add_argument("--top-k", type=int, default=5, help="Number of notes to retrieve")
    
    args = parser.parse_args()
    
    result = ask(args.question, top_k=args.top_k)
    
    print(f"\n🔮 Question: {result['question']}")
    print(f"───────────────────────────────────────────────────")
    print(f"{result['answer']}")
    print(f"───────────────────────────────────────────────────")
    
    if result['sources']:
        print(f"📚 Sources (Confidence: {result['confidence']}):")
        for src in result['sources']:
            print(f"   - {src['title']} (sim: {src['similarity']})")


if __name__ == "__main__":
    main()
