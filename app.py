"""
SecondSelf — Streamlit Web Application (Phase 4: The Oracle)

The main user interface for SecondSelf. Provides a sidebar to capture
new knowledge, and tabs to view the knowledge graph, ask questions via RAG,
and browse the raw database.

Usage:
    streamlit run app.py
"""

import json
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import config
from capture import capture_auto
from classify import classify_all
from link import embed_all_notes, link_all
from build_graph import build_graph
from ask import ask

# ──────────────────────────────────────────────
# Setup & Config
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="SecondSelf — AI Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI polish
st.markdown("""
<style>
    /* Main theme matching graph */
    .stApp {
        background-color: #0f1115;
        color: #e2e8f0;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border-radius: 6px;
        border: none;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #2563eb;
        border-color: transparent;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stTextArea>div>textarea {
        background-color: rgba(30, 41, 59, 0.5);
        color: white;
        border: 1px solid #334155;
    }
    
    /* Chat bubbles */
    .chat-bubble {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        background-color: rgba(30, 41, 59, 0.7);
        border-left: 4px solid #3b82f6;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1e27;
        border-right: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────

@st.cache_data(ttl=5) # Cache for 5s to avoid constant re-reads
def get_stats():
    """Calculate dashboard statistics."""
    stats = {
        "total_notes": 0,
        "total_links": 0,
        "categories": {c: 0 for c in config.PARA_CATEGORIES}
    }
    
    if config.WIKI_DIR.exists():
        for json_file in config.WIKI_DIR.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                stats["total_notes"] += 1
                stats["total_links"] += len(data.get("links", []))
                
                cat = data.get("para_category")
                if cat in stats["categories"]:
                    stats["categories"][cat] += 1
            except:
                pass
                
    # Divide links by 2 since they are bidirectional
    stats["total_links"] = stats["total_links"] // 2
    return stats

def run_full_pipeline(content: str):
    """Run the entire ingestion pipeline end-to-end."""
    try:
        # 1. Capture
        st.toast("📥 Capturing raw data...", icon="⏳")
        capture_auto(content)
        
        # 2. Classify
        st.toast("🧠 LLM is categorizing and summarizing...", icon="⏳")
        classify_all(force_rerun=False)
        
        # 3. Embed & Link
        st.toast("🧮 Computing semantic connections...", icon="⏳")
        embed_all_notes(force_rerun=False)
        link_all()
        
        # 4. Rebuild Graph
        st.toast("🗺️ Rebuilding knowledge graph...", icon="⏳")
        build_graph()
        
        st.success("✅ Capture successfully integrated into your Second Brain!")
        # Clear caches so stats and graph update
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()
        
    except Exception as e:
        st.error(f"Pipeline failed: {e}")


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────

with st.sidebar:
    st.title("🧠 SecondSelf")
    st.markdown("Your autonomous AI Second Brain.")
    st.divider()
    
    # Capture Form
    st.subheader("📥 Capture Knowledge")
    capture_input = st.text_area(
        "Content", 
        placeholder="Paste text, thoughts, or URLs here...",
        height=100,
        label_visibility="collapsed"
    )
    
    if st.button("Capture & Process", use_container_width=True):
        if not capture_input.strip():
            st.warning("Please enter some content to capture.")
        else:
            with st.spinner("Processing..."):
                run_full_pipeline(capture_input)
                
    st.divider()
    
    # Stats Dashboard
    st.subheader("📊 Dashboard")
    stats = get_stats()
    
    col1, col2 = st.columns(2)
    col1.metric("Notes", stats["total_notes"])
    col2.metric("Connections", stats["total_links"])
    
    st.caption("Distribution")
    for cat, count in stats["categories"].items():
        st.progress(
            count / max(1, stats["total_notes"]), 
            text=f"{cat.capitalize()}: {count}"
        )
        
    st.divider()
    
    # Settings
    st.subheader("⚙️ Settings")
    sim_threshold = st.slider(
        "Similarity Threshold", 
        min_value=0.3, max_value=0.9, value=0.65, step=0.05,
        help="Higher = stricter links, Lower = more loose connections"
    )
    top_k = st.slider(
        "RAG Top-K", 
        min_value=1, max_value=10, value=5, step=1,
        help="Number of notes to retrieve for answering questions"
    )
    
    # Small rebuild button
    if st.button("🔄 Force Rebuild Graph", use_container_width=True):
        build_graph()
        st.cache_data.clear()
        st.rerun()


# ──────────────────────────────────────────────
# Main Interface (Tabs)
# ──────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["🗺️ Knowledge Graph", "🔮 Ask Your Brain", "📚 Browse Notes"])

# --- TAB 1: KNOWLEDGE GRAPH ---
with tab1:
    st.header("Visual Explorer")
    
    # Check if graph.html/graph_template.html exists
    html_path = Path("graph_template.html")
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        # We need to inject the actual graph data into the HTML since 
        # Streamlit components run in an iframe and might not load external local JS files correctly
        try:
            with open("graph.json", "r", encoding="utf-8") as f:
                graph_json_str = f.read()
                
            # Inject directly into the head
            injection = f"<script>const graphData = {graph_json_str};</script>"
            html_content = html_content.replace("</head>", f"{injection}\n</head>")
            
            components.html(html_content, height=650, scrolling=False)
        except FileNotFoundError:
            st.warning("graph.json not found. Click 'Force Rebuild Graph' in the sidebar.")
    else:
        st.warning("graph_template.html not found.")

# --- TAB 2: ASK YOUR BRAIN (RAG) ---
with tab2:
    st.header("The Oracle")
    st.markdown("Ask natural language questions. I will answer based *strictly* on your captured knowledge.")
    
    # Init session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        
    # Input box
    question = st.chat_input("What do you want to know about your notes?")
    
    if question:
        # Add to history
        st.session_state.chat_history.append({"role": "user", "content": question})
        
        with st.spinner("Searching brain..."):
            # Run RAG
            # Temporarily patch config if settings were changed
            config.SIMILARITY_THRESHOLD = sim_threshold
            result = ask(question, top_k=top_k)
            
            # Format answer
            answer_content = result["answer"]
            sources = result.get("sources", [])
            
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": answer_content,
                "sources": sources,
                "confidence": result.get("confidence", "none")
            })
            
    # Render chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🧠"):
                st.write(msg["content"])
                
                # Show sources if any exist
                sources = msg.get("sources", [])
                if sources:
                    conf = msg.get("confidence", "none")
                    color = "green" if conf == "high" else "orange" if conf == "medium" else "gray"
                    
                    with st.expander(f"📚 View Sources (Confidence: {conf})"):
                        for src in sources:
                            st.markdown(f"- **{src['title']}** (sim: {src['similarity']})")

# --- TAB 3: BROWSE NOTES ---
with tab3:
    st.header("Raw Database")
    
    # Load all notes into a pandas dataframe
    all_notes = []
    if config.WIKI_DIR.exists():
        for json_file in config.WIKI_DIR.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_notes.append({
                        "Title": data.get("title", "Untitled"),
                        "Category": data.get("para_category", "").capitalize(),
                        "Tags": ", ".join(data.get("tags", [])),
                        "Date": data.get("timestamp", "").split("T")[0],
                        "Summary": data.get("summary", ""),
                        "ID": data.get("id", "")
                    })
            except:
                pass
                
    if all_notes:
        df = pd.DataFrame(all_notes)
        
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            cat_filter = st.selectbox("Filter by Category", ["All"] + [c.capitalize() for c in config.PARA_CATEGORIES])
        with col2:
            search_filter = st.text_input("Search notes...", placeholder="Type to search...")
            
        # Apply filters
        if cat_filter != "All":
            df = df[df["Category"] == cat_filter]
        if search_filter:
            df = df[df["Title"].str.contains(search_filter, case=False, na=False) | 
                    df["Summary"].str.contains(search_filter, case=False, na=False)]
                    
        st.dataframe(
            df[["Title", "Category", "Tags", "Date"]],
            use_container_width=True,
            hide_index=True
        )
        
        st.caption(f"Showing {len(df)} notes.")
    else:
        st.info("No notes found. Capture some knowledge in the sidebar!")
