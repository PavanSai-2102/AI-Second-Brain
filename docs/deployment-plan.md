# 🚀 SecondSelf — Streamlit Deployment Plan

This document outlines the exact steps, requirements, and edge cases for deploying your local Second Brain onto **Streamlit Community Cloud**, allowing you to access it from anywhere!

---

## ⚠️ Important Cloud Limitations

Before deploying, be aware of the following Streamlit Community Cloud limitations (as identified in our Edge Case Audit):

1. **Memory Limits (`EC-4.3.4`):** Streamlit Cloud's free tier has a ~1GB RAM limit. `sentence-transformers` (which installs PyTorch) uses a lot of memory. 
   - **Solution:** We will deploy the app as a **Read-Only / Ask-Only** showcase. You will capture and link notes on your local machine, push the processed `wiki/` JSON files to GitHub, and the cloud app will only load the embeddings to answer questions.
2. **Ephemeral File System (`EC-4.3.1`):** Any new files captured or generated on the cloud server will be permanently deleted when the app goes to sleep or restarts.
   - **Solution:** The cloud version acts as a viewer and chatbot for your existing knowledge base. You should commit your local `wiki/` and `graph.json` files to your GitHub repository so the cloud app can read them upon boot.
3. **Public Visibility (`EC-4.3.6`):** If your GitHub repo is public, your notes are public. 
   - **Solution:** Ensure you do not have highly sensitive data (passwords, bank info) in your `wiki/` before pushing to GitHub. (Or make your repository Private; Streamlit Cloud supports deploying from private repos!).

---

## 🛠️ Step 1: Prepare Your Repository

Ensure your local repository contains all the processed data the web app needs to run:

1. **Generate final graph data:** 
   Run `python3 build_graph.py` on your local machine to ensure `graph.json` and `graph.js` are fully up to date.
2. **Verify requirements:**
   Ensure `requirements.txt` includes everything needed: `streamlit`, `groq`, `sentence-transformers`, `numpy`. (This is already set up correctly).
3. **Commit your `wiki/` data:**
   Normally, large amounts of data shouldn't go to git, but since Streamlit needs it, you must push your processed notes.
   ```bash
   git add wiki/ graph.json graph.js requirements.txt app.py ask.py
   git commit -m "Prepare data for Streamlit deployment"
   git push origin main
   ```

---

## 🌐 Step 2: Deploy on Streamlit Cloud

1. Create a free account at [share.streamlit.io](https://share.streamlit.io/).
2. Click **"New app"** -> **"Deploy from a public/private GitHub repo"**.
3. Connect your GitHub account and authorize Streamlit.
4. Fill in the deployment details:
   - **Repository:** `PavanSai-2102/AI-Second-Brain`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. **DO NOT CLICK DEPLOY YET!** Proceed to Step 3.

---

## 🔐 Step 3: Configure API Secrets

Your local `.env` file containing the `GROQ_API_KEY` was blocked from GitHub by `.gitignore` (which is good!). We must give Streamlit Cloud the key securely.

1. On the Streamlit deployment screen, click **Advanced settings...**
2. In the **Secrets** text box, paste your Groq API key in TOML format:
   ```toml
   GROQ_API_KEY = "gsk_your_api_key_here"
   ```
3. Click **Save**.

---

## 🚀 Step 4: Launch and Test

1. Click **Deploy!**
2. Streamlit will spin up a server, install all packages from `requirements.txt` (this may take 2-4 minutes as it downloads PyTorch), and launch your app.
3. **Testing Checklist:**
   - [ ] Go to the **Knowledge Graph** tab. Ensure it loads the nodes and gradient edges.
   - [ ] Go to the **Browse Notes** tab. Ensure all your notes are visible in the database.
   - [ ] Go to the **Ask Your Brain** tab. Ask a question and ensure Groq successfully answers using your notes as context.

---

## 🔄 Ongoing Maintenance Workflow

Since the deployed app is read-only due to cloud filesystem limitations, here is your workflow for adding new knowledge in the future:

1. Open your local terminal on your Mac.
2. Capture new links/notes locally: `python capture.py auto "..."`
3. Process them locally: `python classify.py` and `python link.py`
4. Rebuild local graph: `python build_graph.py`
5. Push the updates to GitHub: 
   ```bash
   git add wiki/ graph.json graph.js
   git commit -m "Add new knowledge"
   git push
   ```
6. Streamlit Cloud will **automatically detect the GitHub push** and instantly update your live website with the new notes!
