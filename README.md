# 🧠 SecondSelf: AI Second Brain

SecondSelf is a fully autonomous, local AI personal knowledge base. You can dump raw thoughts, web links, or PDF files into it, and it will automatically categorize them, compute semantic connections between them, build an interactive knowledge graph, and allow you to chat with your knowledge via a Retrieval-Augmented Generation (RAG) chatbot.

## ✨ Features

The system is built in 4 interconnected phases:

- 📥 **The Archivist (Capture):** Ingest raw text, scrape web pages, and extract text from PDFs.
- 📚 **The Librarian (Categorize & Link):** Uses the Groq API (Llama 3.3) to automatically summarize and categorize your notes (using the PARA method). It then uses `sentence-transformers` to generate local vector embeddings and automatically discovers bidirectional links between conceptually similar notes.
- 🗺️ **The Cartographer (Visualize):** Parses your entire knowledge base and builds a beautifully interactive, force-directed graph UI (using Cytoscape.js) to visually explore how your thoughts connect.
- 🔮 **The Oracle (Ask & Ship):** A local RAG pipeline and Streamlit Web App that brings it all together. Chat with your notes, browse your database, and view your graph all from one dashboard.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- A free API key from [Groq](https://console.groq.com)

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/PavanSai-2102/AI-Second-Brain.git
cd AI-Second-Brain

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory of the project and add your Groq API key:
```env
GROQ_API_KEY=gsk_your_api_key_here
```

### 4. Running the Application
Launch the Streamlit dashboard:

```bash
streamlit run app.py
```
This will open the web interface in your default browser at `http://localhost:8501`.

## 📁 Project Structure

```
├── app.py                  # Main Streamlit Web App
├── ask.py                  # RAG QA Pipeline (The Oracle)
├── build_graph.py          # Generates graph JSON for the UI (The Cartographer)
├── capture.py              # Ingestion pipeline (The Archivist)
├── classify.py             # LLM categorization & summarization (The Librarian)
├── link.py                 # Semantic auto-linking & embeddings (The Librarian)
├── config.py               # Global configurations & constants
├── graph_template.html     # Interactive Cytoscape UI
├── requirements.txt        # Python dependencies
├── .env                    # (Not tracked) Your API keys
├── raw/                    # (Not tracked) Raw, unprocessed captures
└── wiki/                   # Processed JSON notes with metadata & embeddings
```

## 🧠 Usage Workflow

1. Open the Streamlit App.
2. In the Sidebar, use the **Capture Knowledge** box to paste a thought, a web URL, or the path to a local PDF file.
3. Click **Capture & Process**. The system will:
   - Save the raw content.
   - Summarize and categorize it with the LLM.
   - Embed it and find semantic links to your other notes.
   - Rebuild the knowledge graph.
4. Go to the **Knowledge Graph** tab to visually explore your new note's connections.
5. Go to the **Ask Your Brain** tab to query your knowledge base!

---
*Built as a personal autonomous knowledge engine.*
