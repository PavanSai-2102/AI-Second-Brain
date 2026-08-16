"""
SecondSelf — Streamlit Web Application (Minimalist Dashboard UI)
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
# Setup & Global CSS
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Deep dark minimalist theme
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #000000;
        color: #f3f4f6;
    }
    
    /* Typography */
    h1, h2, h3, h4, p, span, div {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    h1 { font-size: 2.2rem; font-weight: 600; margin-bottom: 0.2rem; }
    h2 { font-size: 1.5rem; font-weight: 500; }
    .subtitle { color: #9ca3af; font-size: 0.95rem; margin-bottom: 2rem; }
    
    /* Hide top padding and sidebar toggle */
    .block-container { padding-top: 4rem; max-width: 1200px; }
    [data-testid="collapsedControl"] { display: none; }
    
    /* Top Navigation Radio Styling */
    div.stRadio > div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        gap: 1.5rem;
        align-items: center;
        border-bottom: 1px solid #1f2937;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }
    /* (Radio circles are kept visible for compatibility) */
    /* Style the labels */
    div[role="radiogroup"] label {
        color: #9ca3af !important;
        font-size: 0.95rem;
        font-weight: 500;
        cursor: pointer;
        padding: 0 !important;
        background: transparent !important;
    }
    div[role="radiogroup"] label[data-checked="true"] p {
        color: #f9fafb !important;
    }
    /* "🧠 Second Brain" brand look */
    div[role="radiogroup"] label:first-child {
        font-weight: 600;
        color: #f9fafb !important;
        margin-right: 2rem;
    }

    /* Metric Cards (Category Grid) */
    .metric-card {
        background-color: #0f0f0f;
        border: 1px solid #262626;
        border-radius: 8px;
        padding: 1.25rem;
        height: 100%;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 0.2rem;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        color: #6b7280;
        text-transform: uppercase;
    }

    /* Action Cards */
    .action-card {
        background-color: #0f0f0f;
        border: 1px solid #262626;
        border-radius: 8px;
        padding: 1.25rem;
        height: 100%;
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .action-card:hover {
        border-color: #4b5563;
    }
    .action-title {
        font-size: 1.1rem;
        font-weight: 500;
        color: #e5e7eb;
        margin-bottom: 0.5rem;
    }
    .action-desc {
        font-size: 0.85rem;
        color: #9ca3af;
        line-height: 1.4;
    }
    
    /* Result/Note Cards */
    .result-card {
        background-color: #0a0a0a;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s;
    }
    .result-card:hover { border-color: #374151; }
    .res-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
    .res-title { font-size: 1.1rem; font-weight: 500; color: #f9fafb; }
    .res-meta { font-size: 0.75rem; color: #6b7280; }
    .res-snippet { font-size: 0.9rem; color: #9ca3af; line-height: 1.5; }

    /* Buttons override */
    .stButton>button {
        background-color: transparent;
        color: #e5e7eb;
        border: 1px solid #374151;
        border-radius: 6px;
    }
    .stButton>button:hover {
        border-color: #6b7280;
        color: #ffffff;
    }
    
    /* Legend Sidebar in Brain Map */
    .legend-box {
        background-color: #0a0a0a;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 1.5rem;
        height: 600px;
    }
    .legend-title { font-size: 0.85rem; color: #9ca3af; margin-bottom: 1.5rem; line-height: 1.4; }
    .legend-item { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; font-size: 0.85rem; color: #d1d5db; }
    .dot { width: 8px; height: 8px; border-radius: 50%; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# State & Helpers
# ──────────────────────────────────────────────

if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"
if "selected_note_id" not in st.session_state:
    st.session_state.selected_note_id = None

@st.cache_data(ttl=5)
def get_dashboard_data():
    notes = []
    categories = {c: 0 for c in config.PARA_CATEGORIES}
    categories["root"] = 0
    total_links = 0
    
    if config.WIKI_DIR.exists():
        for json_file in config.WIKI_DIR.rglob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                    
                cat = data.get("para_category", "root")
                if cat in categories: categories[cat] += 1
                else: categories["root"] += 1
                
                total_links += len(data.get("links", []))
                
                notes.append({
                    "id": data.get("id", ""),
                    "title": data.get("title", "Untitled"),
                    "category": cat,
                    "timestamp": data.get("timestamp", ""),
                    "link_count": len(data.get("links", [])),
                    "summary": data.get("summary", ""),
                    "tags": data.get("tags", [])
                })
            except: pass
            
    notes.sort(key=lambda x: x["timestamp"], reverse=True)
    return {
        "notes": notes,
        "categories": categories,
        "total_notes": len(notes),
        "total_links": total_links // 2
    }

def get_note_by_id(note_id):
    if config.WIKI_DIR.exists():
        for json_file in config.WIKI_DIR.rglob("*.json"):
            if note_id in json_file.name:
                with open(json_file, "r") as f:
                    return json.load(f)
    return None

def change_nav(page):
    st.session_state.nav = page

# ──────────────────────────────────────────────
# Navigation Header
# ──────────────────────────────────────────────

nav_container = st.container()
with nav_container:
    cols = st.columns([2, 1, 1, 1, 1, 5])
    
    with cols[0]:
        st.markdown("<h3 style="margin:0; font-size: 1.1rem; padding-top: 5px;">🧠 Second Brain</h3>", unsafe_allow_html=True)
    
    with cols[1]:
        if st.button("Dashboard", type="primary" if st.session_state.nav == "Dashboard" else "secondary", use_container_width=True):
            st.session_state.nav = "Dashboard"
            st.rerun()
            
    with cols[2]:
        if st.button("Brain Map", type="primary" if st.session_state.nav == "Brain Map" else "secondary", use_container_width=True):
            st.session_state.nav = "Brain Map"
            st.rerun()
            
    with cols[3]:
        if st.button("Ask", type="primary" if st.session_state.nav == "Ask" else "secondary", use_container_width=True):
            st.session_state.nav = "Ask"
            st.rerun()
            
    with cols[4]:
        if st.button("Capture", type="primary" if st.session_state.nav == "Capture" else "secondary", use_container_width=True):
            st.session_state.nav = "Capture"
            st.rerun()

st.markdown("<div style="border-bottom: 1px solid #1f2937; margin-bottom: 2rem;"></div>", unsafe_allow_html=True)

selected_nav = st.session_state.nav

# ──────────────────────────────────────────────
# Page Renderers
# ──────────────────────────────────────────────

if st.session_state.selected_note_id:
    # NOTE DETAILS VIEW
    note = get_note_by_id(st.session_state.selected_note_id)
    if st.button("← Back"):
        st.session_state.selected_note_id = None
        st.rerun()
        
    if note:
        cat = note.get('para_category', 'ROOT').upper()
        title = note.get('title', 'Untitled')
        date = note.get('timestamp', '').split('T')[0]
        tags = " ".join([f"#{t}" for t in note.get('tags', [])])
        
        st.markdown(f"<div style='color:#9ca3af;font-size:0.8rem;letter-spacing:0.05em;margin-bottom:0.5rem;'>{cat}</div>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='margin-bottom:0.5rem;'>{title}</h1>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#6b7280;font-size:0.85rem;margin-bottom:2rem;'>{tags} • created {date}</div>", unsafe_allow_html=True)
        
        st.markdown(f"<div style='border-left: 2px solid #374151; padding-left: 1rem; color: #9ca3af; margin-bottom: 2rem; font-style: italic;'>AI-Generated Summary</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:1.05rem; line-height: 1.6; color: #d1d5db; margin-bottom: 3rem;'>{note.get('summary', 'No content available.')}</div>", unsafe_allow_html=True)
        
        st.markdown("### Related")
        links = note.get('links', [])
        if links:
            for l in links:
                st.markdown(f"- **{l}**")
        else:
            st.markdown("<span style='color:#6b7280;'>No outbound connections.</span>", unsafe_allow_html=True)
            
    else:
        st.error("Note not found.")

elif selected_nav == "Dashboard":
    data = get_dashboard_data()
    
    st.markdown("<h1>Your Second Brain</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>{data['total_notes']} pages across {len([k for k,v in data['categories'].items() if v>0])} categories.</div>", unsafe_allow_html=True)
    
    # Category Grid (3 cols)
    cats = {k: v for k, v in data['categories'].items() if v > 0}
    # Add some empty stubs to match screenshot aesthetic if few categories
    if len(cats) < 4:
        for extra in ["concepts", "events", "daily", "goals", "people"]:
            if extra not in cats: cats[extra] = 0
            
    sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
    
    # Render Grid
    cols = st.columns(4)
    for i, (cat, count) in enumerate(sorted_cats[:8]):
        with cols[i % 4]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{count}</div>
                <div class="metric-label">{cat}</div>
            </div>
            <br>
            """, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Action Cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="action-card">
            <div class="action-title">Brain Map →</div>
            <div class="action-desc">Explore the graph of every page and how they link together.</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="action-card">
            <div class="action-title">Ask →</div>
            <div class="action-desc">Semantic search over everything you've captured.</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="action-card">
            <div class="action-title">Capture →</div>
            <div class="action-desc">Drop a quick note into your inbox for later ingest.</div>
        </div>""", unsafe_allow_html=True)
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Unlinked & Recent Activity
    st.markdown("<div style='color:#6b7280;font-size:0.75rem;font-weight:600;letter-spacing:0.05em;margin-bottom:1rem;'>UNLINKED NOTES</div>", unsafe_allow_html=True)
    unlinked = [n for n in data["notes"] if n["link_count"] == 0]
    if unlinked:
        for u in unlinked[:3]:
            if st.button(f"📄 {u['title']}", key=f"stub_{u['id']}"):
                st.session_state.selected_note_id = u['id']
                st.rerun()
    else:
        st.markdown("<span style='color:#374151;'>All notes are connected!</span>", unsafe_allow_html=True)

    st.markdown("<br><div style='color:#6b7280;font-size:0.75rem;font-weight:600;letter-spacing:0.05em;margin-bottom:1rem;'>RECENT ACTIVITY</div>", unsafe_allow_html=True)
    for n in data["notes"][:5]:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"<div style='font-size:0.9rem; color:#9ca3af;'>• <b>{n['title']}</b> - {n['summary'][:100]}...</div>", unsafe_allow_html=True)
            with col2:
                if st.button("View", key=f"rec_{n['id']}"):
                    st.session_state.selected_note_id = n['id']
                    st.rerun()

elif selected_nav == "Brain Map":
    data = get_dashboard_data()
    st.markdown("<h1>Brain Map</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>{data['total_notes']} pages, {data['total_links']} links — built live from every link in the vault.</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns([3, 1])
    
    with c1:
        # Embed Cytoscape
        html_path = Path("graph_template.html")
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            try:
                with open("graph.json", "r", encoding="utf-8") as f:
                    graph_json_str = f.read()
                injection = f"<script>const graphData = {graph_json_str};</script>"
                if '<script src="graph.js"></script>' in html_content:
                    html_content = html_content.replace('<script src="graph.js"></script>', injection)
                else:
                    html_content = html_content.replace("</head>", f"{injection}\n</head>")
                components.html(html_content, height=600, scrolling=False)
            except:
                st.warning("Missing graph.json")
        else:
            st.warning("graph_template.html missing")
            
    with c2:
        # Side Legend
        colors = {
            "root": "#9ca3af", "people": "#f59e0b", "places": "#10b981", 
            "events": "#eab308", "finance": "#06b6d4", "career": "#8b5cf6",
            "health": "#ef4444", "projects": "#3b82f6", "goals": "#ec4899",
            "decisions": "#14b8a6", "daily": "#64748b", "concepts": "#6366f1"
        }
        
        legend_html = "<div class='legend-box'><div class='legend-title'>Click a node to preview the page. Colors group pages by category; drag to rearrange, scroll to zoom.</div><hr style='border-color:#1f2937; margin-bottom: 20px;'>"
        for cat, color in colors.items():
            legend_html += f"<div class='legend-item'><div class='dot' style='background-color: {color}; box-shadow: 0 0 8px {color};'></div> {cat}</div>"
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)
        
        if st.button("🔄 Rebuild Graph", use_container_width=True):
            build_graph()
            st.rerun()

elif selected_nav == "Ask":
    st.markdown("<h1>Ask your second brain</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Semantic search over every page, run locally against embeddings.</div>", unsafe_allow_html=True)
    
    if not os.getenv("GROQ_API_KEY"):
        st.warning("⚠️ GROQ_API_KEY is missing in environment/secrets!")
    
    with st.form(key="ask_form"):
        cols = st.columns([5, 1])
        with cols[0]:
            query = st.text_input("Search", placeholder="What did his February blood report flag?", label_visibility="collapsed")
        with cols[1]:
            submit = st.form_submit_button("Ask", use_container_width=True)
            
    if submit and query:
        with st.spinner("Searching..."):
            result = ask(query, top_k=6)
            sources = result.get("sources", [])
            
            for src in sources:
                # Mock percentage for aesthetic based on sim score
                sim = float(src['similarity'])
                pct = int(sim * 100)
                cat = "root" # We don't return category in ask.py currently, fallback to root
                
                st.markdown(f"""
                <div class="result-card">
                    <div class="res-header">
                        <div class="res-title">{src['title']}</div>
                        <div class="res-meta">{pct}% match · {cat}</div>
                    </div>
                    <div class="res-snippet">{src['snippet']}</div>
                </div>
                """, unsafe_allow_html=True)

elif selected_nav == "Capture":
    st.markdown("<h1>Capture</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Drop a quick note into your inbox for later ingest.</div>", unsafe_allow_html=True)
    st.caption("⚠️ Note: On Cloud, captured data is temporary.")
    
    content = st.text_area("Content", placeholder="Paste thoughts, links, or text...", height=200, label_visibility="collapsed")
    
    if st.button("Capture & Process", type="primary"):
        if content.strip():
            with st.spinner("Processing through AI pipeline..."):
                capture_auto(content)
                classify_all(force_rerun=False)
                embed_all_notes(force_rerun=False)
                link_all()
                build_graph()
                st.success("Successfully captured and linked into your Second Brain!")
        else:
            st.warning("Enter some content.")
